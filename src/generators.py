from faker import Faker
from providers import DNIProvider, PlateProvider, VINProvider
from tqdm import tqdm
import random
import unicodedata
import os
from io_utils import load_plate_series, load_postal_and_phone
    

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
    # Inyectar mapping a PlateProvider y registrarlo
    PlateProvider.series_by_year = series_by_year
    fake.add_provider(PlateProvider)
    fake.add_provider(VINProvider)
    return fake


def generate_users(fake, n, data_dir=None, cp_to_municipalities=None, prov_to_tlf=None, prov_code_to_name=None, show_progress: bool = False):
    users = []
    landline_prob = 0.539  # Probabilidad de que la persona tenga teléfono fijo
    emails_generados = set()
    landlines_generados = set()

    # Cargar datos si no se proporcionan
    if cp_to_municipalities is None or prov_to_tlf is None or prov_code_to_name is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(script_dir)
        if data_dir is None:
            base = os.path.join(repo_root, 'data')
        elif not os.path.isabs(data_dir):
            base = os.path.join(repo_root, data_dir)
        else:
            base = data_dir
        cp_file = os.path.join(base, 'codigos_postales_municipios.csv')
        tlf_file = os.path.join(base, 'prov_tlf.csv')
        cp_to_municipalities, prov_to_tlf, prov_code_to_name = load_postal_and_phone(cp_file, tlf_file)

    if cp_to_municipalities:
        valid_cps = list(cp_to_municipalities.keys())
        iterator = tqdm(range(n), desc="Generando usuarios") if show_progress else range(n)
        for _ in iterator:
            dni = fake.unique.dni()
            # Teléfono móvil
            prefijo_movil = str(random.choice([6, 7]))
            phone_mobile = prefijo_movil + ''.join(str(random.randint(0, 9)) for _ in range(8))

            # Selección de ciudad y provincia
            cp = random.choice(valid_cps)
            municipio = random.choice(cp_to_municipalities[cp])
            prov_code = cp[:2]
            provincia = prov_code_to_name.get(prov_code, "Desconocida")

            # Teléfono fijo: usar prefijo de provincia si existe y completar hasta 9 dígitos
            phone_landline = ""
            if prov_code in prov_to_tlf:
                prov_prefijo = prov_to_tlf[prov_code]
                restantes = max(0, 9 - len(prov_prefijo))
                candidate = prov_prefijo + ''.join(str(random.randint(0, 9)) for _ in range(restantes))

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
        # Fallback si no hay CSV cargado
        iterator = tqdm(range(n), desc="Generando usuarios") if show_progress else range(n)
        for _ in iterator:
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

def generate_vehicles(fake, users, show_progress: bool = False):
    vehicles = []
    used_plates = set()
    used_vins = set()
    # Probabilidades: [0 coches, 1 coche, 2 coches, 3 coches]
    probs = [0.15, 0.50, 0.25, 0.10]  

    iterator_users = tqdm(users, desc="Generando vehículos") if show_progress else users
    for user in iterator_users:
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
