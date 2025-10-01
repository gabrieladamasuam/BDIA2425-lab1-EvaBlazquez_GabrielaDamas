import os
import argparse
import csv
from faker import Faker
from faker.providers import BaseProvider
from tqdm import tqdm
import random
import unicodedata
import sqlite3
import sys
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except Exception:
    pa = None
    pq = None

# ===================== Funciones auxiliares =====================

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
    # Validar existencia de ficheros requeridos
    if not os.path.exists(csv_cp):
        raise FileNotFoundError(f"No se encontró el archivo requerido: {csv_cp}")
    if not os.path.exists(csv_tlf):
        raise FileNotFoundError(f"No se encontró el archivo requerido: {csv_tlf}")

    # Cargar códigos postales y municipios
    with open(csv_cp, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cp = row['codigo_postal'].zfill(5)
            municipio = row['municipio_nombre'].strip()
            cp_to_municipalities.setdefault(cp, []).append(municipio)
    print(f"Cargados {len(cp_to_municipalities)} códigos postales únicos")

    # Cargar prefijos de teléfono por provincia (indexados por código CP inicial)
    with open(csv_tlf, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            prov_cp = row['postal_code'].zfill(2)   # columna con prefijo CP
            prov_name = row['name'].strip()         # nombre de provincia
            phone_code = row['phone_code'].strip()  # prefijo de teléfono
            prov_to_tlf[prov_cp] = phone_code
            prov_code_to_name[prov_cp] = prov_name

    return cp_to_municipalities, prov_to_tlf, prov_code_to_name

# ===================== Providers =====================

# Provider de DNI
class DNIProvider(BaseProvider):
    __letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
    def dni_number(self) -> int:
        return self.generator.random_int(min=11111111, max=99999999)
    def dni_control_letter(self, num: int) -> str:
        return self.__letters[num % 23]
    def dni(self) -> str:
        n = self.dni_number()
        return f"{n:08d}-{self.dni_control_letter(n)}"

class PlateProvider(BaseProvider):
    def __init__(self, generator, series_by_year):
        super().__init__(generator)
        self.series_by_year = series_by_year
        self.min_year = min(series_by_year.keys()) if series_by_year else 2000
        self.max_year = max(series_by_year.keys()) if series_by_year else 2025

    def plate(self, year: int = None) -> str:
        if year is None:
            year = random.randint(self.min_year, self.max_year)
        series = self.series_by_year.get(year, ["ZZZ"])
        letters = random.choice(series)
        nums = random.randint(0, 9999)
        return f"{nums:04d}{letters}"

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

class VINProvider(BaseProvider):
    chars = "0123456789ABCDEFGHJKLMNPRSTUVWXYZ"  # sin I, O, Q

    year_codes = {
        2000: "Y", 2001: "1", 2002: "2", 2003: "3", 2004: "4", 2005: "5", 2006: "6", 2007: "7", 2008: "8", 
        2009: "9", 2010: "A", 2011: "B", 2012: "C", 2013: "D", 2014: "E", 2015: "F", 2016: "G", 2017: "H", 
        2018: "J", 2019: "K", 2020: "L", 2021: "M", 2022: "N", 2023: "P", 2024: "R", 2025: "S"
    }

    transl = {
        **{str(i): i for i in range(10)},
        **dict(zip("ABCDEFGHJKLMNPRSTUVWXYZ", 
                   [1,2,3,4,5,6,7,8,1,2,3,4,5,6,7,8,9,2,3,4,5,6,7,8,9]))
    }
    
    weights = [8,7,6,5,4,3,2,10,0,9,8,7,6,5,4,3,2]

    def vin(self, wmi: str, year: int) -> str:
        # Generar VDS (4-8)
        vds = ''.join(random.choice(self.chars) for _ in range(5))
        
        # Año en el carácter 10
        year_char = self.year_codes.get(year, "X")
        
        # Planta de ensamblaje (11)
        plant = random.choice(self.chars)
        
        # Número de serie (12-17)
        serial = ''.join(random.choice(self.chars) for _ in range(6))
        
        # VIN provisional con dígito 9 temporal y luego lo sustituimos
        vin_temp = f"{wmi}{vds}0{year_char}{plant}{serial}"
        
        # Calcular checksum para el 9º carácter
        check_digit = self._calculate_checksum(vin_temp)
        
        # VIN final
        vin_final = f"{wmi}{vds}{check_digit}{year_char}{plant}{serial}"
        return vin_final

    def _calculate_checksum(self, vin17: str) -> str:
        total = 0
        for i, char in enumerate(vin17):
            val = self.transl.get(char, 0)
            total += val * self.weights[i]
        remainder = total % 11
        return "X" if remainder == 10 else str(remainder)
    

# ===================== Generadores =====================

def build_generators(seed=None, locale='es_ES', series_csv_path=None):
    fake = Faker(locale)
    if seed is not None:
        Faker.seed(seed)
        random.seed(seed)
    fake.add_provider(DNIProvider)
    # Añadimos proveedores de matrícula y VIN (series cargadas desde CSV)
    if series_csv_path is None:
        raise ValueError("Debe proporcionarse la ruta al CSV de series de matrículas")
    series_by_year = load_plate_series(series_csv_path)
    fake.add_provider(PlateProvider, series_by_year)
    fake.add_provider(VINProvider)
    return fake


def generate_users(fake, cp_to_municipalities, prov_to_tlf, prov_code_to_name, n):
    users = []
    landline_prob = 0.539  # Probabilidad de que la persona tenga teléfono fijo
    emails_generados = set()
    landlines_generados = set()

    if not cp_to_municipalities:
        raise RuntimeError("No se cargaron códigos postales desde el CSV. Comprueba la ruta de datos.")

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
    return users

VEHICLE_CATEGORIES = [
    "urbano", "sedán", "berlina", "cupé", "descapotable", "deportivo", 
    "todoterreno", "monovolumen", "SUV"
]

def generate_vehicles(fake, users, vehicles_per_user_avg=1.2):
    vehicles = []
    n_users = len(users)
    dnis = [u["DNI"] for u in users]
    expected_total = int(n_users * vehicles_per_user_avg)
    
    used_plates = set()
    used_vins = set()

    for _ in tqdm(range(expected_total), desc="Generando vehículos"):
        owner = random.choice(dnis)
        year = random.randint(2000, 2025)

        plate = fake.plate(year)
        while plate in used_plates:
            plate = fake.plate(year)
        used_plates.add(plate)

        manufacturer = random.choice(MANUFACTURERS)
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
            "Category": random.choice(VEHICLE_CATEGORIES),
            "OwnerDNI": owner
        }
        vehicles.append(veh)

    return vehicles

# ===================== Ficheros =====================
def write_csv(data, filepath):
    if not data:
        return
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(list(data[0].keys()))
        for row in data:
            writer.writerow([row.get(k, "") for k in row.keys()])

def write_parquet(data, filepath):
    if not data:
        return
    if pa is None or pq is None:
        print(f"pyarrow no está instalado. Omitiendo Parquet: {filepath}")
        return
    table = pa.Table.from_pylist(data)
    pq.write_table(table, filepath, compression='snappy')
    
# ===================== SGBD =====================
def write_sqlite(users, vehicles, dbfile):
    con = sqlite3.connect(dbfile)
    try:
        cur = con.cursor()
        # Asegurar integridad referencial en SQLite
        cur.execute("PRAGMA foreign_keys = ON;")
        cur.execute("DROP TABLE IF EXISTS vehicles")
        cur.execute("DROP TABLE IF EXISTS users")
        cur.execute("""CREATE TABLE users (
                        Name TEXT, DNI TEXT PRIMARY KEY, Email TEXT,
                        PhoneMobile TEXT, PhoneLandline TEXT, Address TEXT,
                        City TEXT, PostalCode TEXT, Province TEXT
                       )""")
        cur.execute("""CREATE TABLE vehicles (
                        Plate TEXT PRIMARY KEY, VIN TEXT, Year INTEGER,
                        Make TEXT, Model TEXT, Category TEXT, OwnerDNI TEXT,
                        FOREIGN KEY (OwnerDNI) REFERENCES users(DNI)
                       )""")
        if users:
            usr_rows = [(u['Name'], u['DNI'], u['Email'], u['PhoneMobile'], u['PhoneLandline'],
                         u['Address'], u['City'], u['PostalCode'], u['Province']) for u in users]
            cur.executemany("INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)", usr_rows)
        if vehicles:
            veh_rows = [(v['Plate'], v['VIN'], v['Year'], v['Make'], v['Model'], v['Category'], v['OwnerDNI']) for v in vehicles]
            cur.executemany("INSERT INTO vehicles VALUES (?,?,?,?,?,?,?)", veh_rows)
        con.commit()
    finally:
        con.close()

# ===================== Main =====================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_users", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--data_dir", type=str, default="data")
    parser.add_argument("--out_dir", type=str, default="output")
    parser.add_argument("--plate_series_csv", type=str, default="data/series_matriculas.csv", help="Ruta al CSV con series de matrículas por año")
    args = parser.parse_args()

    # Resolver rutas relativas respecto a la raíz del repo (carpeta padre de src)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    data_dir = args.data_dir if os.path.isabs(args.data_dir) else os.path.join(repo_root, args.data_dir)
    out_dir = args.out_dir if os.path.isabs(args.out_dir) else os.path.join(repo_root, args.out_dir)

    cp_file = os.path.join(data_dir, "codigos_postales_municipios.csv")
    tlf_file = os.path.join(data_dir, "prov_tlf.csv")
    series_file = args.plate_series_csv if os.path.isabs(args.plate_series_csv) else os.path.join(repo_root, args.plate_series_csv)
    # Validar ficheros de datos requeridos y abortar si faltan
    try:
        cp_to_municipalities, prov_to_tlf, prov_code_to_name = load_postal_and_phone(cp_file, tlf_file)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("Indica el directorio correcto con --data_dir (por defecto 'data' en la raíz del proyecto).")
        sys.exit(1)
    os.makedirs(out_dir, exist_ok=True)

    fake = build_generators(seed=args.seed, series_csv_path=series_file)
    users = generate_users(fake, cp_to_municipalities, prov_to_tlf, prov_code_to_name, args.n_users)
    vehicles = generate_vehicles(fake, users, vehicles_per_user_avg=1.3)

    users_csv = os.path.join(out_dir, "users.csv")
    vehicles_csv = os.path.join(out_dir, "vehicles.csv")
    write_csv(users, users_csv)
    write_csv(vehicles, vehicles_csv)
    print(f"Wrote CSV to {users_csv} y {vehicles_csv}")

    # Parquet
    users_parquet = os.path.join(out_dir, "users.parquet")
    vehicles_parquet = os.path.join(out_dir, "vehicles.parquet")
    write_parquet(users, users_parquet)
    write_parquet(vehicles, vehicles_parquet)
    if pa is not None and pq is not None:
        print(f"Wrote Parquet to {users_parquet} y {vehicles_parquet}")

    # SQLite
    sqlite_file = os.path.join(out_dir, "fake_data.sqlite3")
    write_sqlite(users, vehicles, sqlite_file)
    print(f"Wrote SQLite DB to {sqlite_file}")

if __name__ == "__main__":
    main()