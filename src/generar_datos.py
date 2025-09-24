# Generador de datos sintéticos de usuarios y vehículos


from faker import Faker
from faker.providers import BaseProvider
import random

# Provider personalizado para DNI español
class DNIProvider(BaseProvider):
    """Provider para generar DNI"""
    __letters = 'TRWAGMYFPDXBNJZSQVHLCKE'  # letras válidas del dígito de control

    def dni_number(self) -> int:
        """Genera un número de DNI con un máximo de 8 dígitos"""
        return self.generator.random_int(min=11111111, max=99999999)

    def dni_control_letter(self, num):
        """Genera la letra de control para el número de DNI proporcionado por parámetro"""
        return self.__letters[num % 23]

    def dni(self) -> str:
        """Genera una cadena con los ocho dígitos del número de dni y la letra de control separados por un guión"""
        num = self.dni_number()
        control = self.dni_control_letter(num)
        return f'{num:08d}-{control}'

# Inicializar Faker y añadir el provider
faker = Faker('es_ES')
faker.add_provider(DNIProvider)

# Parámetros de generación
NUM_USUARIOS = 1000
NUM_VEHICULOS = 2000

# Categorías de vehículos
CATEGORIAS = [
    'urbanos', 'sedán', 'berlina', 'cupé', 'descapotable',
    'deportivo', 'todoterreno', 'monovolumen', 'SUV'
]

# Generar usuarios
usuarios = []
dnis = set()
while len(usuarios) < NUM_USUARIOS:
    # Generar DNI único
    while True:
        dni_str = faker.dni()
        if dni_str not in dnis:
            dnis.add(dni_str)
            break
    usuario = {
        'nombre': faker.name(),
        'dni': dni_str,
        'email': faker.email(),
        'movil': faker.phone_number(),
        'fijo': faker.phone_number(),
        'direccion': faker.address().replace('\n', ', '),
        'ciudad': faker.city(),
        'codigo_postal': faker.postcode(),
        'provincia': faker.state()
    }
    usuarios.append(usuario)

# Generar vehículos
vehiculos = []
for _ in range(NUM_VEHICULOS):
    usuario = random.choice(usuarios)
    vehiculo = {
        'matricula': faker.license_plate(),
        'bastidor': faker.unique.bothify(text='??##############'),
        'anio': random.randint(1990, 2025),
        'fabricante': faker.company(),
        'modelo': faker.word(),
        'categoria': random.choice(CATEGORIAS),
        'dni_usuario': usuario['dni']
    }
    vehiculos.append(vehiculo)

# Ejemplo de impresión de los primeros registros
def mostrar_ejemplo():
    print('Ejemplo de usuario:')
    print(usuarios[0])
    print('\nEjemplo de vehículo:')
    print(vehiculos[0])

if __name__ == '__main__':
    mostrar_ejemplo()
