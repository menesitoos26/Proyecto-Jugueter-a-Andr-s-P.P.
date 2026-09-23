# API de juguete para practicar testing (unitario + integración) con SQLite

Mini API REST en **Python + Flask + SQLite**, con el mínimo de dependencias
posible, pensada para que el alumnado practique cómo escribir **tests
unitarios** y **tests de integración** contra una base de datos real antes
de automatizarlos en un pipeline de despliegue (CI/CD).

No usa ORM ni migraciones: las rutas de Flask ejecutan SQL directamente
con el módulo `sqlite3` (de la librería estándar de Python, sin instalar
nada extra). La idea es que todo el comportamiento de la API —incluida la
parte de base de datos— se pueda leer y entender en un único fichero
(`app.py`), para centrar el esfuerzo en el testing y no en la arquitectura.

> ⚠️ Este proyecto es **solo para practicar**. El login usa un token
> aleatorio simple en vez de JWT, no hay HTTPS, rate limiting, pool de
> conexiones, etc. No lo despliegues tal cual en un entorno real.

---

## Índice

1. [¿Qué hace exactamente la app?](#qué-hace-exactamente-la-app)
2. [Dependencias](#dependencias)
3. [Estructura del proyecto](#estructura-del-proyecto)
4. [Cómo lanzar la app](#cómo-lanzar-la-app)
5. [Endpoints y ejemplos](#endpoints)
6. [La base de datos SQLite](#la-base-de-datos-sqlite)
8. [Sugerencia de uso en clase](#sugerencia-de-uso-en-clase)
9. [Ideas para ampliar](#ideas-para-ampliar-opcional)

---

## ¿Qué hace exactamente la app?

Es una API REST con **tres bloques de funcionalidad**, todos guardados en
una base de datos SQLite (fichero `app.db`):

1. **Autenticación** (`/registro`, `/login`)
   - `POST /registro` crea un usuario nuevo (`username` + `password`). La
     contraseña **nunca** se guarda en texto plano: se guarda su hash
     (`werkzeug.security.generate_password_hash`). Si el `username` ya
     existe, devuelve `409 Conflict`.
   - `POST /login` comprueba usuario + contraseña y, si son correctos,
     genera un **token aleatorio** (`secrets.token_hex(16)`, no es un
     JWT) y lo guarda en la tabla `tokens`. Ese token es lo que hay que
     mandar luego en cada petición protegida.
   - Cualquier ruta protegida exige la cabecera
     `Authorization: Bearer <token>`. Si falta, es inválido o no existe
     en la tabla `tokens`, la API responde `401 Unauthorized`.

2. **CRUD de productos** (`/productos`)
   - Crear, listar, obtener uno, actualizar y borrar productos.
   - Cada producto tiene `nombre` (texto), `precio` (número >= 0) y
     `stock` (entero >= 0). Si los datos no cumplen esas reglas, la API
     responde `400 Bad Request` con un mensaje describiendo el problema.
   - Pedir/actualizar/borrar un producto que no existe responde
     `404 Not Found`.

3. **CRUD de clientes** (`/clientes`)
   - Igual que productos, pero cada cliente tiene `nombre`, `email`
     (debe tener formato válido, tipo `algo@dominio.algo`) y `telefono`
     (opcional; si no se manda, se guarda como cadena vacía).

Todo el estado vive en SQLite, no en memoria: si paras la app y la
vuelves a arrancar, los productos, clientes y usuarios siguen ahí (los
tokens de sesión también, mientras no se borre `app.db`).

## Dependencias

Solo dos, a propósito:

- **Flask** — para servir la API.
- **pytest** — para ejecutar los tests (solo hace falta para desarrollo/CI,
  no para ejecutar la app).

`sqlite3` viene incluido en la librería estándar de Python: no hace falta
instalar ningún driver ni base de datos aparte.

## Estructura del proyecto

```
.
├── app.py                        # Toda la API: rutas, SQL, validaciones, auth
├── requirements.txt               # Dependencias para ejecutar la app (Flask)
├── requirements-dev.txt           # + pytest, para desarrollo/tests
├── pytest.ini                     # Configuración de pytest
└── tests/
    ├── conftest.py                 # Fixtures compartidas (app, client, tokens...)
    ├── unit/                       # Tests unitarios: funciones puras, sin HTTP
    │   ├── test_validaciones.py      # Reglas de negocio (validar_producto, etc.)
    │   ├── test_tokens.py            # Generación de tokens
    │   └── test_db.py                # Esquema SQL (init_db), sin pasar por Flask
    └── integration/                # Tests de integración: peticiones HTTP reales
        ├── test_auth.py               # Registro, login, protección por token
        ├── test_productos.py          # CRUD completo de productos
        ├── test_clientes.py           # CRUD completo de clientes
        └── test_persistencia.py       # Comprueba los datos leyendo el .db "a mano"
```

Dentro de `app.py` el código está organizado (de arriba a abajo) en:

- Definición del esquema SQL e `init_db` / `get_db` / `cerrar_db`
  (todo lo relacionado con la conexión a SQLite).
- Funciones de **validación** puras (`validar_registro`, `validar_producto`,
  `validar_cliente`) y `generar_token`.
- El decorador `requiere_token`, que protege las rutas.
- `crear_app(db_path)`: la *app factory* con todas las rutas de Flask.

## Cómo lanzar la app

```bash
# 1. Crear y activar un entorno virtual
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / Mac
source .venv/bin/activate

# 2. Instalar dependencias (Flask + pytest)
pip install -r requirements-dev.txt

# 3. Arrancar la API
python app.py
```

La API queda escuchando en `http://127.0.0.1:5000`. La primera vez que se
ejecuta crea automáticamente el fichero **`app.db`** (SQLite) en la raíz
del proyecto con las tablas necesarias. Puedes abrir ese fichero con
cualquier visor de SQLite (DB Browser for SQLite, la extensión de VS Code,
`sqlite3 app.db` por línea de comandos...) para ver los datos que va
guardando la API mientras la usas.

Si solo quieres instalar lo necesario para ejecutar la app (sin pytest,
por ejemplo en un entorno de producción de mentira), usa
`pip install -r requirements.txt` en el paso 2.

Para parar la app: `Ctrl+C` en la terminal donde está corriendo.

## Endpoints

Todos los endpoints (salvo `/registro` y `/login`) requieren la cabecera:

```
Authorization: Bearer <token>
```

El token se obtiene haciendo login.

| Método | Ruta               | Descripción                  | Requiere token |
|--------|--------------------|-------------------------------|:---:|
| POST   | `/registro`        | Crear un usuario               |  No |
| POST   | `/login`           | Iniciar sesión, devuelve token |  No |
| GET    | `/productos`       | Listar productos                | Sí |
| POST   | `/productos`       | Crear producto                  | Sí |
| GET    | `/productos/<id>`  | Obtener un producto              | Sí |
| PUT    | `/productos/<id>`  | Actualizar un producto           | Sí |
| DELETE | `/productos/<id>`  | Borrar un producto               | Sí |
| GET    | `/clientes`        | Listar clientes                  | Sí |
| POST   | `/clientes`        | Crear cliente                    | Sí |
| GET    | `/clientes/<id>`   | Obtener un cliente                | Sí |
| PUT    | `/clientes/<id>`   | Actualizar un cliente             | Sí |
| DELETE | `/clientes/<id>`   | Borrar un cliente                 | Sí |

### Ejemplo de uso con curl

```bash
# 1. Registro
curl -X POST http://127.0.0.1:5000/registro \
  -H "Content-Type: application/json" \
  -d '{"username": "ana", "password": "1234"}'

# 2. Login (guarda el token de la respuesta)
curl -X POST http://127.0.0.1:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "ana", "password": "1234"}'

# 3. Crear un producto (sustituye <TOKEN>)
curl -X POST http://127.0.0.1:5000/productos \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"nombre": "Teclado", "precio": 19.99, "stock": 10}'
```

### Cuerpos esperados

- **Producto**: `{"nombre": str, "precio": número >= 0, "stock": entero >= 0}`
- **Cliente**: `{"nombre": str, "email": str (formato válido), "telefono": str (opcional)}`

## La base de datos SQLite

El esquema (tablas `usuarios`, `tokens`, `productos`, `clientes`) se define
en `app.py` como una única cadena SQL (`ESQUEMA_SQL`) y se crea con
`init_db(ruta)`, que usa `CREATE TABLE IF NOT EXISTS` y por tanto se puede
llamar varias veces sin problema.

Cada petición HTTP abre su propia conexión sqlite a través de `get_db()`
(guardada en el objeto `g` de Flask) y la cierra automáticamente al
terminar (`cerrar_db`, registrado con `app.teardown_appcontext`). Es el
patrón recomendado por la propia documentación de Flask para trabajar con
SQLite sin librerías adicionales.

Puntos pensados para que se note el comportamiento real de una base de
datos (y no un simple diccionario):

- La columna `username` tiene una restricción `UNIQUE`: intentar
  registrar dos veces el mismo usuario falla a nivel de base de datos, no
  solo por una comprobación en Python.
- Los `id` de productos y clientes los genera SQLite (`AUTOINCREMENT`), no
  un contador en Python.
- Los datos sobreviven a un reinicio del proceso, porque están en un
  fichero `.db` en disco (pruébalo: crea un producto, para la app con
  `Ctrl+C`, vuelve a arrancarla y comprueba que sigue estando en
  `GET /productos`).

