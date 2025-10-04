#!/usr/bin/env python3
"""
generate_and_store.py

Genera datos sintéticos (usuarios + vehículos) y permite guardarlos en:
CSV, Parquet, JSON (anidado y separado), Avro, SQLite, PostgreSQL y MongoDB.

Uso:
    python generate_and_store.py --n_users 10000 --seed 42 --out_dir output --cp_file codigos_postales_municipios.csv

Requisitos: Faker, pyarrow, fastavro, psycopg2, pymongo, tqdm
"""
import os
import argparse
import json
import csv
from faker import Faker
from faker.providers import BaseProvider
from tqdm import tqdm
import random
from datetime import datetime
import sqlite3
import fastavro
import pyarrow as pa
import pyarrow.parquet as pq

# Opcionales para PG / Mongo
try:
    import psycopg2
    from psycopg2.extras import execute_batch
except Exception:
    psycopg2 = None

try:
    import pymongo
except Exception:
    pymongo = None


# -------------------------
# Cargar datos de códigos postales desde el CSV
# -------------------------
def load_postal_codes(csv_filepath='codigos_postales_municipios.csv'):
    """
    Carga los datos de códigos postales y crea un mapeo:
    - cp_to_municipalities: código postal -> lista de municipios
    - cp_to_province: código postal -> provincia (por los 2 primeros dígitos del CP)
    """
    cp_to_municipalities = {}
    cp_to_province = {}

    CP_TO_PROVINCE = {
        "01": "Álava", "02": "Albacete", "03": "Alicante", "04": "Almería",
        "05": "Ávila", "06": "Badajoz", "07": "Islas Baleares", "08": "Barcelona",
        "09": "Burgos", "10": "Cáceres", "11": "Cádiz", "12": "Castellón",
        "13": "Ciudad Real", "14": "Córdoba", "15": "A Coruña", "16": "Cuenca",
        "17": "Girona", "18": "Granada", "19": "Guadalajara", "20": "Guipúzcoa",
        "21": "Huelva", "22": "Huesca", "23": "Jaén", "24": "León",
        "25": "Lleida", "26": "La Rioja", "27": "Lugo", "28": "Madrid",
        "29": "Málaga", "30": "Murcia", "31": "Navarra", "32": "Ourense",
        "33": "Asturias", "34": "Palencia", "35": "Las Palmas", "36": "Pontevedra",
        "37": "Salamanca", "38": "Santa Cruz de Tenerife", "39": "Cantabria",
        "40": "Segovia", "41": "Sevilla", "42": "Soria", "43": "Tarragona",
        "44": "Teruel", "45": "Toledo", "46": "Valencia", "47": "Valladolid",
        "48": "Vizcaya", "49": "Zamora", "50": "Zaragoza", "51": "Ceuta",
        "52": "Melilla"
    }

    try:
        with open(csv_filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cp = row['codigo_postal'].zfill(5)
                municipio_nombre = row['municipio_nombre'].strip()
                provincia_codigo = cp[:2]
                provincia_nombre = CP_TO_PROVINCE.get(provincia_codigo, "Desconocida")

                cp_to_municipalities.setdefault(cp, []).append(municipio_nombre)
                cp_to_province[cp] = provincia_nombre

        print(f"Cargados {len(cp_to_municipalities)} códigos postales únicos")
        return cp_to_municipalities, cp_to_province, CP_TO_PROVINCE

    except FileNotFoundError:
        print(f"⚠️ No se encontró el archivo {csv_filepath}, usando fallback aleatorio")
        return {}, {}, CP_TO_PROVINCE


# Inicializar
cp_to_municipalities, cp_to_province, CP_TO_PROVINCE = load_postal_codes()


# -------------------------
# Providers personalizados
# -------------------------
class DNIProvider(BaseProvider):
    __letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
    def dni_number(self) -> int:
        return self.generator.random_int(min=11111111, max=99999999)
    def dni_control_letter(self, num:int) -> str:
        return self.__letters[num % 23]
    def dni(self) -> str:
        n = self.dni_number()
        return f"{n:08d}-{self.dni_control_letter(n)}"

class PlateProvider(BaseProvider):
    consonants = "BCDFGHJKLMNPQRSTVWXYZ"
    def plate(self) -> str:
        nums = random.randint(0, 9999)
        letters = ''.join(random.choice(self.consonants) for _ in range(3))
        return f"{nums:04d}{letters}"

class VINProvider(BaseProvider):
    chars = "0123456789ABCDEFGHJKLMNPRSTUVWXYZ"
    def vin(self) -> str:
        return ''.join(random.choice(self.chars) for _ in range(17))


# -------------------------
# Generadores
# -------------------------
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

    if cp_to_municipalities:
        valid_cps = list(cp_to_municipalities.keys())
        for _ in tqdm(range(n), desc="Generando usuarios coherentes"):
            dni = fake.unique.dni()
            phone_mobile = fake.unique.phone_number()

            cp = random.choice(valid_cps)
            municipio = random.choice(cp_to_municipalities[cp])
            provincia = cp_to_province[cp]

            users.append({
                "Name": fake.name(),
                "DNI": dni,
                "Email": fake.ascii_company_email(),
                "PhoneMobile": phone_mobile,
                "PhoneLandline": fake.phone_number(),
                "Address": fake.street_address(),
                "City": municipio,
                "PostalCode": cp,
                "Province": provincia
            })
    else:
        for _ in tqdm(range(n), desc="Generando usuarios aleatorios (sin CSV)"):
            dni = fake.unique.dni()
            phone_mobile = fake.unique.phone_number()
            cp_num = random.randint(1000, 52999)
            cp = f"{cp_num:05d}"
            prov = CP_TO_PROVINCE.get(cp[:2], "Desconocida")
            municipio = f"Municipio-{cp}"

            users.append({
                "Name": fake.name(),
                "DNI": dni,
                "Email": fake.ascii_company_email(),
                "PhoneMobile": phone_mobile,
                "PhoneLandline": fake.phone_number(),
                "Address": fake.street_address(),
                "City": municipio,
                "PostalCode": cp,
                "Province": prov
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
    
    for _ in tqdm(range(expected_total), desc="Generando vehículos"):
        owner = random.choice(dnis)
        veh = {
            "Plate": fake.plate(),
            "VIN": fake.vin(),
            "Year": random.randint(1990, datetime.now().year),
            "Make": fake.company(),
            "Model": fake.word().title(),
            "Category": random.choice(VEHICLE_CATEGORIES),
            "OwnerDNI": owner
        }
        vehicles.append(veh)
        
    return vehicles


# -------------------------
# Escritura en ficheros
# -------------------------
def write_csv(data, filepath):
    if not data:
        return
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(list(data[0].keys()))
        for row in data:
            writer.writerow([row.get(k, "") for k in row.keys()])

def write_parquet(data, filepath, schema=None):
    table = pa.Table.from_pylist(data, schema=schema)
    pq.write_table(table, filepath, compression='snappy')

def write_json_separate(data, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def write_json_nested(users, vehicles, filepath):
    dni_map = {}
    for v in vehicles:
        dni_map.setdefault(v["OwnerDNI"], []).append(v)
    nested = []
    for u in users:
        ucopy = u.copy()
        ucopy["Vehicles"] = dni_map.get(u["DNI"], [])
        nested.append(ucopy)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(nested, f, ensure_ascii=False, indent=2)

def write_avro(data, schema, filepath):
    with open(filepath, 'wb') as out:
        fastavro.writer(out, schema, data)


# -------------------------
# SGBD: SQLite, PostgreSQL, MongoDB
# -------------------------
def write_sqlite(users, vehicles, dbfile):
    con = sqlite3.connect(dbfile)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS users")
    cur.execute("DROP TABLE IF EXISTS vehicles")
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
    
    usr_rows = [(u['Name'], u['DNI'], u['Email'], u['PhoneMobile'], u['PhoneLandline'],
                 u['Address'], u['City'], u['PostalCode'], u['Province']) for u in users]
    veh_rows = [(v['Plate'], v['VIN'], v['Year'], v['Make'], v['Model'], v['Category'], v['OwnerDNI']) for v in vehicles]
    
    cur.executemany("INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)", usr_rows)
    cur.executemany("INSERT INTO vehicles VALUES (?,?,?,?,?,?,?)", veh_rows)
    con.commit()
    con.close()

def write_postgres(users, vehicles, conn_info):
    if psycopg2 is None:
        print("psycopg2 no está instalado. Omitiendo PostgreSQL.")
        return
    conn = psycopg2.connect(conn_info)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS vehicles")
    cur.execute("DROP TABLE IF EXISTS users")
    cur.execute("""
        CREATE TABLE users (
            Name TEXT, DNI TEXT PRIMARY KEY, Email TEXT,
            PhoneMobile TEXT, PhoneLandline TEXT, Address TEXT,
            City TEXT, PostalCode TEXT, Province TEXT
        )""")
    cur.execute("""
        CREATE TABLE vehicles (
            Plate TEXT PRIMARY KEY, VIN TEXT, Year INTEGER,
            Make TEXT, Model TEXT, Category TEXT, OwnerDNI TEXT,
            FOREIGN KEY (OwnerDNI) REFERENCES users(DNI)
        )""")
    conn.commit()
    
    usr_rows = [(u['Name'], u['DNI'], u['Email'], u['PhoneMobile'], u['PhoneLandline'],
                 u['Address'], u['City'], u['PostalCode'], u['Province']) for u in users]
    veh_rows = [(v['Plate'], v['VIN'], v['Year'], v['Make'], v['Model'], v['Category'], v['OwnerDNI']) for v in vehicles]
    
    execute_batch(cur, "INSERT INTO users VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", usr_rows, page_size=1000)
    execute_batch(cur, "INSERT INTO vehicles VALUES (%s,%s,%s,%s,%s,%s,%s)", veh_rows, page_size=1000)
    conn.commit()
    cur.close()
    conn.close()

def write_mongo(users, vehicles, dbname='fake_db', host='mongodb://localhost:27017/'):
    if pymongo is None:
        print("pymongo no está instalado. Omitiendo MongoDB.")
        return
    client = pymongo.MongoClient(host)
    db = client[dbname]
    db.users.drop()
    db.vehicles.drop()
    if users:
        db.users.insert_many(users)
    if vehicles:
        db.vehicles.insert_many(vehicles)
    client.close()


# -------------------------
# Avro esquemas
# -------------------------
def avro_schema_users():
    return {
        "name": "User",
        "type": "record",
        "fields": [
            {"name":"Name","type":"string"},
            {"name":"DNI","type":"string"},
            {"name":"Email","type":"string"},
            {"name":"PhoneMobile","type":"string"},
            {"name":"PhoneLandline","type":"string"},
            {"name":"Address","type":"string"},
            {"name":"City","type":"string"},
            {"name":"PostalCode","type":"string"},
            {"name":"Province","type":"string"}
        ]
    }

def avro_schema_vehicles():
    return {
        "name": "Vehicle",
        "type": "record",
        "fields": [
            {"name":"Plate","type":"string"},
            {"name":"VIN","type":"string"},
            {"name":"Year","type":"int"},
            {"name":"Make","type":"string"},
            {"name":"Model","type":"string"},
            {"name":"Category","type":"string"},
            {"name":"OwnerDNI","type":"string"}
        ]
    }


# -------------------------
# CLI y flujo principal
# -------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_users", type=int, default=1000, help="Número de usuarios a generar")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--out_dir", type=str, default="output")
    parser.add_argument("--cp_file", type=str, default="codigos_postales_municipios.csv", help="Ruta al archivo CSV de códigos postales")
    parser.add_argument("--pg_conn", type=str, default=None, help="Cadena de conexión PostgreSQL")
    parser.add_argument("--mongo_uri", type=str, default="mongodb://localhost:27017/")
    args = parser.parse_args()

    global cp_to_municipalities, cp_to_province, CP_TO_PROVINCE
    cp_to_municipalities, cp_to_province, CP_TO_PROVINCE = load_postal_codes(args.cp_file)

    os.makedirs(args.out_dir, exist_ok=True)

    fake = build_generators(seed=args.seed)
    users = generate_users(fake, args.n_users)
    vehicles = generate_vehicles(fake, users, vehicles_per_user_avg=1.3)

    # CSV
    users_csv = os.path.join(args.out_dir, "users.csv")
    vehicles_csv = os.path.join(args.out_dir, "vehicles.csv")
    write_csv(users, users_csv)
    write_csv(vehicles, vehicles_csv)
    print(f"Wrote CSV to {users_csv}, {vehicles_csv}")

    # Parquet
    users_parquet = os.path.join(args.out_dir, "users.parquet")
    vehicles_parquet = os.path.join(args.out_dir, "vehicles.parquet")
    write_parquet(users, users_parquet)
    write_parquet(vehicles, vehicles_parquet)
    print(f"Wrote Parquet to {users_parquet}, {vehicles_parquet}")

    # JSON
    json_nested_file = os.path.join(args.out_dir, "users_nested.json")
    write_json_nested(users, vehicles, json_nested_file)
    
    users_json = os.path.join(args.out_dir, "users.json")
    vehicles_json = os.path.join(args.out_dir, "vehicles.json")
    write_json_separate(users, users_json)
    write_json_separate(vehicles, vehicles_json)
    print(f"Wrote JSON files to {json_nested_file}, {users_json}, {vehicles_json}")

    # Avro
    users_avro = os.path.join(args.out_dir, "users.avro")
    vehicles_avro = os.path.join(args.out_dir, "vehicles.avro")
    write_avro(users, avro_schema_users(), users_avro)
    write_avro(vehicles, avro_schema_vehicles(), vehicles_avro)
    print(f"Wrote Avro to {users_avro}, {vehicles_avro}")

    # SQLite
    sqlite_file = os.path.join(args.out_dir, "fake_data.sqlite3")
    write_sqlite(users, vehicles, sqlite_file)
    print(f"Wrote SQLite DB to {sqlite_file}")

    # PostgreSQL
    if args.pg_conn:
        try:
            write_postgres(users, vehicles, args.pg_conn)
            print("Wrote data to PostgreSQL.")
        except Exception as e:
            print("Error escribiendo en PostgreSQL:", e)

    # MongoDB
    try:
        write_mongo(users, vehicles, dbname="fake_db", host=args.mongo_uri)
        print("Wrote data to MongoDB (if servidor disponible).")
    except Exception as e:
        print("Error escribiendo en MongoDB:", e)

if __name__ == "__main__":
    main()
