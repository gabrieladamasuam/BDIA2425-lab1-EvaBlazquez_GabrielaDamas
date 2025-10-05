from faker import Faker
from providers import DNIProvider, PlateProvider, VINProvider
from tqdm import tqdm
import random
import unicodedata
import os
from io_utils import load_postal_and_phone
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

# Rutas
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
_CP_FILE = os.path.join(_REPO_ROOT, 'data', 'codigos_postales_municipios.csv')
_TLF_FILE = os.path.join(_REPO_ROOT, 'data', 'prov_tlf.csv')
_MODELS_FILE = os.path.join(_REPO_ROOT, 'data', 'models_by_make.csv')
_CP_TO_MUNICIPALITIES, _PROV_TO_TLF, _PROV_CODE_TO_NAME = load_postal_and_phone(_CP_FILE, _TLF_FILE)

def _load_models_by_make(path: str):
    mapping = {}
    if not os.path.exists(path):
        return mapping
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            make = row['make'].strip()
            model = row['model'].strip()
            category = row['category'].strip()
            mapping.setdefault(make, []).append({"model": model, "category": category})
    return mapping

_MODELS_BY_MAKE = _load_models_by_make(_MODELS_FILE)


def build_generators(seed=None, locale='es_ES'):
    fake = Faker(locale)
    if seed is not None:
        Faker.seed(seed)
        random.seed(seed)
    fake.add_provider(DNIProvider)
    fake.add_provider(PlateProvider)
    fake.add_provider(VINProvider)
    return fake

def generate_users(fake, n):
    users = []
    landline_prob = 0.539  # Probabilidad de que la persona tenga teléfono fijo
    emails_generados = set()
    landlines_generados = set()

    valid_cps = list(_CP_TO_MUNICIPALITIES.keys())

    def normaliza_email(s):
        s = s.lower()
        s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
        return s.replace(' ', '').replace('.', '').replace('-', '')

    def gen_phone_mobile():
        prefijo_movil = str(random.choice([6, 7]))
        return prefijo_movil + ''.join(str(random.randint(0, 9)) for _ in range(8))

    def gen_phone_landline(prov_code: str) -> str:
        if prov_code in _PROV_TO_TLF:
            prov_prefijo = _PROV_TO_TLF[prov_code]
            restantes = max(0, 9 - len(prov_prefijo))
            candidate = prov_prefijo + ''.join(str(random.randint(0, 9)) for _ in range(restantes))
            if random.random() < landline_prob and candidate not in landlines_generados:
                landlines_generados.add(candidate)
                return candidate
        return ""

    for _ in range(n):
        dni = fake.unique.dni()
        nombre = fake.name()

        # Ubicación
        cp = random.choice(valid_cps)
        municipio = random.choice(_CP_TO_MUNICIPALITIES[cp])
        prov_code = cp[:2]
        provincia = _PROV_CODE_TO_NAME.get(prov_code, "Desconocida")

        # Teléfonos
        phone_mobile = gen_phone_mobile()
        phone_landline = gen_phone_landline(prov_code)

        # Email único
        partes = nombre.split()
        nombre_email = normaliza_email(partes[0])
        apellidos_email = normaliza_email(''.join(partes[1:])) if len(partes) > 1 else ''
        dominio = fake.free_email_domain()
        email = f"{nombre_email}{apellidos_email}@{dominio}"
        i = 1
        while email in emails_generados:
            email = f"{nombre_email}{apellidos_email}{i}@{dominio}"
            i += 1
        emails_generados.add(email)

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
            # Año con distribución más realista (más peso en años recientes)
            years = list(range(2000, 2026))
            weights = [1]*5 + [3]*5 + [6]*11 + [4]*3 + [2]*2
            year = random.choices(years, weights=weights, k=1)[0]
            plate = fake.plate(year)
            while plate in used_plates:
                plate = fake.plate(year)
            used_plates.add(plate)

            manufacturer = fake.random_element(MANUFACTURERS)
            vin = fake.vin(manufacturer["wmi"], year)
            while vin in used_vins:
                vin = fake.vin(manufacturer["wmi"], year)
            used_vins.add(vin)
            
            # Elegir modelo y categoría coherentes con la marca desde CSV
            model_info_list = _MODELS_BY_MAKE.get(manufacturer["make"])
            if model_info_list:
                model_info = fake.random_element(model_info_list)
                model = model_info["model"]
                category = model_info["category"]
            else:
                model = fake.word().title()
                category = "desconocido"

            veh = {
                "Plate": plate,
                "VIN": vin,
                "Year": year,
                "Make": manufacturer["make"],
                "Model": model,
                "Category": category,
                "UserDNI": user["DNI"]
            }
            vehicles.append(veh)

    return vehicles
