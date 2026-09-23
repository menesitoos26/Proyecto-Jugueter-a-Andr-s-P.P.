import unittest


from app import (
    validar_registro,
    validar_producto,
    validar_cliente
)

class TestValidarRegistroUsuario(unittest.TestCase):
    
    def test_validar_registro_usuario(self):
        # Arrange
        data = {
            "username": "Juan",
            "password": "123456"
            }
        
        # Act
        result = validar_registro(data)

        # Assert
        self.assertEqual(result, None)

    def test_validar_registro_usuario_invalido_contraseña_corta(self):
        # Arrange
        data = {
            "username": "Juan",
            "password": "123"
            }

        # Act
        result = validar_registro(data)

        # Assert
        self.assertEqual(result, None)

class TestValidarProducto(unittest.TestCase):
    
    def test_validar_producto(self):
        # Arrange
        data = {
            "nombre": "Producto1",
            "precio": 10.5,
            "stock": 5
            }
        
        # Act
        result = validar_producto(data)

        # Assert
        self.assertEqual(result, None)

    def test_validar_producto_precio_invalido(self):
        # Arrange
        data = {
            "nombre": "Producto1",
            "precio": -10.5,
            "stock": 5
            }

        # Act
        result = validar_producto(data)

        # Assert
        self.assertEqual(result, None)

    def test_validar_producto_stock_invalido(self):
        # Arrange
        data = {
            "nombre": "Producto1",
            "precio": 10.5,
            "stock": -5
            }

        # Act
        result = validar_producto(data)

        # Assert
        self.assertEqual(result, None)

class TestValidarCliente(unittest.TestCase):

    def test_validar_cliente(self):
        # Arrange
        data = {
            "nombre": "Cliente1",
            "email": "cliente1@example.com"
            }
        # Act
        result =validar_cliente(data)

        # Assert
        self.assertEqual(result, None)

    def test_validar_cliente_email_invalido(self):
        # Arrange
        data = {
            "nombre": "Cliente1",
            "email": "cliente1example.com"
            }
        # Act
        result = validar_cliente(data)

        # Assert
        self.assertEqual(result, None)

    def test_validar_cliente_nombre_invalido(self):
        # Arrange
        data = {
            "nombre": "",
            "email": "cliente1@example.com"
            }
        # Act
        result = validar_cliente(data)

        # Assert
        self.assertEqual(result, None)

    
if __name__ == '__main__':
    unittest.main()

