"""
API de juguete respaldada por SQLite, para practicar tests unitarios y de
integracion contra una base de datos real (no un diccionario en memoria).

OBJETIVO DIDACTICO: el codigo es intencionadamente simple. No hay ORM, no
hay capas ni repositorios: las rutas de Flask ejecutan SQL directamente
usando el modulo "sqlite3" de la libreria estandar de Python. Asi se puede
ver de un vistazo que pasa en la base de datos con cada peticion.

Endpoints:
    POST   /registro            -> crear usuario
    POST   /login                -> obtener token
    GET    /productos            -> listar productos      (requiere token)
    POST   /productos            -> crear producto        (requiere token)
    GET    /productos/<id>       -> obtener un producto    (requiere token)
    PUT    /productos/<id>       -> actualizar un producto (requiere token)
    DELETE /productos/<id>       -> borrar un producto     (requiere token)
    GET    /clientes             -> listar clientes        (requiere token)
    POST   /clientes             -> crear cliente          (requiere token)
    GET    /clientes/<id>        -> obtener un cliente     (requiere token)
    PUT    /clientes/<id>        -> actualizar un cliente  (requiere token)
    DELETE /clientes/<id>        -> borrar un cliente      (requiere token)
"""

import re
import secrets
import sqlite3
from functools import wraps

from flask import Flask, current_app, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

# ---------------------------------------------------------------------------
# Base de datos SQLite
# ---------------------------------------------------------------------------
# Nombre del fichero por defecto cuando se ejecuta "python app.py". Los
# tests usan un fichero distinto (temporal) para no pisar esta base de
# datos ni depender de ejecuciones anteriores.
BASE_DE_DATOS_POR_DEFECTO = "app.db"

ESQUEMA_SQL = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tokens (
    token TEXT PRIMARY KEY,
    username TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    precio REAL NOT NULL,
    stock INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    email TEXT NOT NULL,
    telefono TEXT
);
"""


def init_db(ruta_db):
    """Crea el fichero de base de datos (si no existe) y las tablas (si
    no existen). Se puede llamar varias veces sin problema: es idempotente
    porque el esquema usa "CREATE TABLE IF NOT EXISTS"."""
    conexion = sqlite3.connect(ruta_db)
    try:
        conexion.executescript(ESQUEMA_SQL)
        conexion.commit()
    finally:
        conexion.close()


def get_db():
    """Devuelve la conexion sqlite de la peticion actual, abriendola la
    primera vez que se pide dentro de cada peticion (patron estandar de
    Flask con el objeto "g")."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row  # permite leer filas como dict
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def cerrar_db(excepcion=None):
    """Cierra la conexion sqlite al terminar cada peticion."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ---------------------------------------------------------------------------
# Validaciones (funciones puras, sin Flask ni SQL de por medio -> faciles
# de testear con tests unitarios normales, sin levantar la app ni la BD).
# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validar_registro(data):
    """Devuelve un mensaje de error (str) si los datos no son validos,
    o None si todo esta correcto."""
    if not isinstance(data, dict):
        return "Cuerpo de la peticion invalido"
    username = data.get("username")
    password = data.get("password")
    if not username or not isinstance(username, str):
        return "El campo username es obligatorio"
    if not password or not isinstance(password, str) or len(password) < 4:
        return "El campo password debe tener al menos 4 caracteres"
    return None


def validar_producto(data):
    if not isinstance(data, dict):
        return "Cuerpo de la peticion invalido"
    nombre = data.get("nombre")
    precio = data.get("precio")
    stock = data.get("stock")
    if not nombre or not isinstance(nombre, str):
        return "El campo nombre es obligatorio"
    if isinstance(precio, bool) or not isinstance(precio, (int, float)) or precio < 0:
        return "El campo precio debe ser un numero >= 0"
    if isinstance(stock, bool) or not isinstance(stock, int) or stock < 0:
        return "El campo stock debe ser un entero >= 0"
    return None


def validar_cliente(data):
    if not isinstance(data, dict):
        return "Cuerpo de la peticion invalido"
    nombre = data.get("nombre")
    email = data.get("email")
    if not nombre or not isinstance(nombre, str):
        return "El campo nombre es obligatorio"
    if not email or not isinstance(email, str) or not EMAIL_RE.match(email):
        return "El campo email no es valido"
    return None


def generar_token():
    """Genera un token aleatorio. No es un JWT, es solo una cadena
    aleatoria que guardamos en la tabla "tokens" como sesion valida."""
    return secrets.token_hex(16)


# ---------------------------------------------------------------------------
# Decorador de autenticacion
# ---------------------------------------------------------------------------
def requiere_token(vista):
    @wraps(vista)
    def envoltorio(*args, **kwargs):
        cabecera = request.headers.get("Authorization", "")
        if not cabecera.startswith("Bearer "):
            return jsonify(error="Falta el token de autenticacion"), 401
        token = cabecera[len("Bearer "):].strip()
        db = get_db()
        fila = db.execute("SELECT username FROM tokens WHERE token = ?", (token,)).fetchone()
        if fila is None:
            return jsonify(error="Token invalido o caducado"), 401
        g.usuario = fila["username"]
        return vista(*args, **kwargs)
    return envoltorio


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def crear_app(db_path=BASE_DE_DATOS_POR_DEFECTO):
    app = Flask(__name__)
    app.config["DATABASE"] = db_path
    init_db(db_path)
    app.teardown_appcontext(cerrar_db)

    @app.get("/")
    def index():
        return jsonify(mensaje="API de prueba. Ver /registro, /login, /productos, /clientes")

    # ---- Autenticacion ----------------------------------------------------
    @app.post("/registro")
    def registro():
        data = request.get_json(silent=True)
        error = validar_registro(data)
        if error:
            return jsonify(error=error), 400
        db = get_db()
        username = data["username"]
        existe = db.execute("SELECT 1 FROM usuarios WHERE username = ?", (username,)).fetchone()
        if existe is not None:
            return jsonify(error="Ese usuario ya existe"), 409
        db.execute(
            "INSERT INTO usuarios (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(data["password"])),
        )
        db.commit()
        return jsonify(mensaje="Usuario creado correctamente"), 201

    @app.post("/login")
    def login():
        data = request.get_json(silent=True) or {}
        username = data.get("username")
        password = data.get("password")
        db = get_db()
        usuario = db.execute(
            "SELECT password_hash FROM usuarios WHERE username = ?", (username,)
        ).fetchone()
        if usuario is None or not check_password_hash(usuario["password_hash"], password or ""):
            return jsonify(error="Usuario o contrasena incorrectos"), 401
        token = generar_token()
        db.execute("INSERT INTO tokens (token, username) VALUES (?, ?)", (token, username))
        db.commit()
        return jsonify(token=token), 200

    # ---- Productos ----------------------------------------------------
    @app.get("/productos")
    @requiere_token
    def listar_productos():
        db = get_db()
        filas = db.execute("SELECT * FROM productos ORDER BY id").fetchall()
        return jsonify([dict(fila) for fila in filas]), 200

    @app.post("/productos")
    @requiere_token
    def crear_producto():
        data = request.get_json(silent=True)
        error = validar_producto(data)
        if error:
            return jsonify(error=error), 400
        db = get_db()
        cursor = db.execute(
            "INSERT INTO productos (nombre, precio, stock) VALUES (?, ?, ?)",
            (data["nombre"], data["precio"], data["stock"]),
        )
        db.commit()
        producto = db.execute(
            "SELECT * FROM productos WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return jsonify(dict(producto)), 201

    @app.get("/productos/<int:id_>")
    @requiere_token
    def obtener_producto(id_):
        db = get_db()
        producto = db.execute("SELECT * FROM productos WHERE id = ?", (id_,)).fetchone()
        if producto is None:
            return jsonify(error="Producto no encontrado"), 404
        return jsonify(dict(producto)), 200

    @app.put("/productos/<int:id_>")
    @requiere_token
    def actualizar_producto(id_):
        db = get_db()
        existente = db.execute("SELECT 1 FROM productos WHERE id = ?", (id_,)).fetchone()
        if existente is None:
            return jsonify(error="Producto no encontrado"), 404
        data = request.get_json(silent=True)
        error = validar_producto(data)
        if error:
            return jsonify(error=error), 400
        db.execute(
            "UPDATE productos SET nombre = ?, precio = ?, stock = ? WHERE id = ?",
            (data["nombre"], data["precio"], data["stock"], id_),
        )
        db.commit()
        producto = db.execute("SELECT * FROM productos WHERE id = ?", (id_,)).fetchone()
        return jsonify(dict(producto)), 200

    @app.delete("/productos/<int:id_>")
    @requiere_token
    def eliminar_producto(id_):
        db = get_db()
        existente = db.execute("SELECT 1 FROM productos WHERE id = ?", (id_,)).fetchone()
        if existente is None:
            return jsonify(error="Producto no encontrado"), 404
        db.execute("DELETE FROM productos WHERE id = ?", (id_,))
        db.commit()
        return "", 204

    # ---- Clientes -------------------------------------------------------
    @app.get("/clientes")
    @requiere_token
    def listar_clientes():
        db = get_db()
        filas = db.execute("SELECT * FROM clientes ORDER BY id").fetchall()
        return jsonify([dict(fila) for fila in filas]), 200

    @app.post("/clientes")
    @requiere_token
    def crear_cliente():
        data = request.get_json(silent=True)
        error = validar_cliente(data)
        if error:
            return jsonify(error=error), 400
        db = get_db()
        cursor = db.execute(
            "INSERT INTO clientes (nombre, email, telefono) VALUES (?, ?, ?)",
            (data["nombre"], data["email"], data.get("telefono", "")),
        )
        db.commit()
        cliente = db.execute(
            "SELECT * FROM clientes WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return jsonify(dict(cliente)), 201

    @app.get("/clientes/<int:id_>")
    @requiere_token
    def obtener_cliente(id_):
        db = get_db()
        cliente = db.execute("SELECT * FROM clientes WHERE id = ?", (id_,)).fetchone()
        if cliente is None:
            return jsonify(error="Cliente no encontrado"), 404
        return jsonify(dict(cliente)), 200

    @app.put("/clientes/<int:id_>")
    @requiere_token
    def actualizar_cliente(id_):
        db = get_db()
        existente = db.execute("SELECT 1 FROM clientes WHERE id = ?", (id_,)).fetchone()
        if existente is None:
            return jsonify(error="Cliente no encontrado"), 404
        data = request.get_json(silent=True)
        error = validar_cliente(data)
        if error:
            return jsonify(error=error), 400
        db.execute(
            "UPDATE clientes SET nombre = ?, email = ?, telefono = ? WHERE id = ?",
            (data["nombre"], data["email"], data.get("telefono", ""), id_),
        )
        db.commit()
        cliente = db.execute("SELECT * FROM clientes WHERE id = ?", (id_,)).fetchone()
        return jsonify(dict(cliente)), 200

    @app.delete("/clientes/<int:id_>")
    @requiere_token
    def eliminar_cliente(id_):
        db = get_db()
        existente = db.execute("SELECT 1 FROM clientes WHERE id = ?", (id_,)).fetchone()
        if existente is None:
            return jsonify(error="Cliente no encontrado"), 404
        db.execute("DELETE FROM clientes WHERE id = ?", (id_,))
        db.commit()
        return "", 204

    return app


if __name__ == "__main__":
    crear_app().run(debug=True)
