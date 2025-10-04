from faker import Faker
from providers import DNIProvider, PlateProvider, VINProvider
from tqdm import tqdm
import random
import unicodedata
import os
import csv
    

MANUFACTURERS = [
    {"make": "Seat", "wmi": "VSS"},
    {"make": "Volkswagen", "wmi": "WVW"},
    {"make": "Audi", "wmi": "WAU"},
    {"make": "BMW", "wmi": "WBA"},
    {"make": "Mercedes-Benz", "wmi": "WDB"},
    {"make": "Renault", "wmi": "VF1"},
    {"make": "Peugeot", "wmi": "VF3"},
    {"make": "Toyota", "wmi": "JT2"},
    {"make": "Ford", "wmi": "WF0"},
    {"make": "Citroën", "wmi": "VF7"}
]

VEHICLE_CATEGORIES = [
    "urbano", "sedán", "berlina", "cupé", "descapotable", "deportivo", 
    "todoterreno", "monovolumen", "SUV"
]

def load_plate_series(csv_series: str):
    """Carga series de matrículas por año desde un CSV (columnas: year, series)."""
    if not os.path.exists(csv_series):
        raise FileNotFoundError(f"No se encontró el archivo requerido: {csv_series}")
    series_by_year = {}
    with open(csv_series, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            y = int(row['year'])
            s = row['series'].strip()
            series_by_year.setdefault(y, []).append(s)
    return series_by_year

# Cargar datos de códigos postales y prefijos de teléfono
def load_postal_and_phone(csv_cp='codigos_postales_municipios.csv', csv_tlf='prov_tlf.csv'):
    cp_to_municipalities = {}
    prov_to_tlf = {}
    prov_code_to_name = {}
    # Cargar códigos postales y municipios
    try:
        with open(csv_cp, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cp = row['codigo_postal'].zfill(5)
                municipio = row['municipio_nombre'].strip()
                cp_to_municipalities.setdefault(cp, []).append(municipio)
        print(f"Cargados {len(cp_to_municipalities)} códigos postales únicos")
    except FileNotFoundError:
        print(f"No se encontró el archivo {csv_cp}, usando fallback aleatorio")
        cp_to_municipalities = {}
    # Cargar prefijos de teléfono por provincia (indexados por código CP inicial)
    try:
        with open(csv_tlf, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                prov_cp = row['postal_code'].zfill(2)   # columna con prefijo CP
                prov_name = row['name'].strip()         # nombre de provincia
                phone_code = row['phone_code'].strip()  # prefijo de teléfono
                prov_to_tlf[prov_cp] = phone_code
                prov_code_to_name[prov_cp] = prov_name
    except FileNotFoundError:
        print(f"No se encontró el archivo {csv_tlf}, usando fallback aleatorio")
        prov_to_tlf = {}
        prov_code_to_name = {}

    return cp_to_municipalities, prov_to_tlf, prov_code_to_name



def build_generators(seed=None, locale='es_ES', series_csv_path=None):
    fake = Faker(locale)
    if seed is not None:
        Faker.seed(seed)
        random.seed(seed)
    fake.add_provider(DNIProvider)
    # Cargar series de matrículas desde CSV y registrar provider
    if series_csv_path is None:
        # Resolver por defecto respecto a la raíz del repo: ../data/series_matriculas.csv
        script_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(script_dir)
        series_csv_path = os.path.join(repo_root, 'data', 'series_matriculas.csv')
    series_by_year = load_plate_series(series_csv_path)
    fake.add_provider(PlateProvider, series_by_year)
    fake.add_provider(VINProvider)
    return fake


def generate_users(fake, cp_to_municipalities, prov_to_tlf, prov_code_to_name, n):
    users = []
    landline_prob = 0.539  # Probabilidad de que la persona tenga teléfono fijo
    emails_generados = set()
    landlines_generados = set()

    if cp_to_municipalities:
        valid_cps = list(cp_to_municipalities.keys())

        for _ in tqdm(range(n), desc="Generando usuarios coherentes"):
            dni = fake.unique.dni()
            # Teléfono móvil
            prefijo_movil = str(random.choice([6, 7]))
            phone_mobile = prefijo_movil + ''.join(str(random.randint(0, 9)) for _ in range(8))

            # Selección de ciudad y provincia
            cp = random.choice(valid_cps)
            municipio = random.choice(cp_to_municipalities[cp])
            prov_code = cp[:2]
            provincia = prov_code_to_name.get(prov_code, "Desconocida")

            # Teléfono fijo: usar prefijo de provincia si existe
            phone_landline = ""
            if prov_code in prov_to_tlf:
                prov_prefijo = prov_to_tlf[prov_code]
                candidate = prov_prefijo + ''.join(str(random.randint(0, 9)) for _ in range(7))

                if random.random() < landline_prob and candidate not in landlines_generados:
                    phone_landline = candidate
                    landlines_generados.add(candidate)

            # Nombre y email
            nombre = fake.name()
            def normaliza_email(s):
                s = s.lower()
                s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
                s = s.replace(' ', '').replace('.', '').replace('-', '')
                return s

            partes = nombre.split()
            nombre_email = normaliza_email(partes[0])
            apellidos_email = normaliza_email(''.join(partes[1:])) if len(partes) > 1 else ''
            dominio = fake.free_email_domain()
            email_base = f"{nombre_email}{apellidos_email}@{dominio}"

            # Evitar emails duplicados
            email = email_base
            contador = 1
            while email in emails_generados:
                email = f"{nombre_email}{apellidos_email}{contador}@{dominio}"
                contador += 1
            emails_generados.add(email)

            # Agregar usuario
            users.append({
                "Name": nombre,
                "DNI": dni,
                "Email": email,
                "PhoneMobile": phone_mobile,
                "PhoneLandline": phone_landline,
                "Address": fake.street_address(),
                "City": municipio,
                "PostalCode": cp,
                "Province": provincia
            })
    else:
        # Fallback si no hay CSV
        for _ in tqdm(range(n), desc="Generando usuarios aleatorios (sin CSV)"):
            dni = fake.unique.dni()
            phone_mobile = fake.unique.phone_number()
            cp = f"{random.randint(1000, 52999):05d}"
            municipio = f"Municipio-{cp}"

            phone_landline = fake.phone_number() if random.random() < landline_prob else ""

            users.append({
                "Name": fake.name(),
                "DNI": dni,
                "Email": fake.ascii_company_email(),
                "PhoneMobile": phone_mobile,
                "PhoneLandline": phone_landline,
                "Address": fake.street_address(),
                "City": municipio,
                "PostalCode": cp,
                "Province": "Desconocida"
            })
    return users

def generate_vehicles(fake, users):
    vehicles = []
    used_plates = set()
    used_vins = set()
    # Probabilidades: [0 coches, 1 coche, 2 coches, 3 coches]
    probs = [0.15, 0.50, 0.25, 0.10]  

    for user in tqdm(users):
        n_cars = random.choices([0, 1, 2, 3], weights=probs, k=1)[0]
        for _ in range(n_cars):
            year = random.randint(2000, 2025)
            plate = fake.plate(year)
            while plate in used_plates:
                plate = fake.plate(year)
            used_plates.add(plate)

            manufacturer = fake.random_element(MANUFACTURERS)
            vin = fake.vin(manufacturer["wmi"], year)
            while vin in used_vins:
                vin = fake.vin(manufacturer["wmi"], year)
            used_vins.add(vin)

            veh = {
                "Plate": plate,
                "VIN": vin,
                "Year": year,
                "Make": manufacturer["make"],
                "Model": fake.word().title(),
                "Category": fake.random_element(VEHICLE_CATEGORIES),
                "UserDNI": user["DNI"]
            }
            vehicles.append(veh)

    return vehicles
