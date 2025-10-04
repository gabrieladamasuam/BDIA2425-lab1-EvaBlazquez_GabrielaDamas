import os
import csv
import json
import sqlite3
from typing import Dict, List, Tuple

# pyarrow opcional para Parquet
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except Exception:
    pa = None
    pq = None

try:
    from fastavro import writer as avro_writer, parse_schema
except Exception:
    avro_writer = None
    parse_schema = None

# ===================== Loaders (entrada de datos) =====================

def load_plate_series(csv_series: str) -> Dict[int, List[str]]:
    """Carga series de matrículas por año desde un CSV (columnas: year, series)."""
    if not os.path.exists(csv_series):
        raise FileNotFoundError(f"No se encontró el archivo requerido: {csv_series}")
    series_by_year: Dict[int, List[str]] = {}
    with open(csv_series, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            y = int(row['year'])
            s = row['series'].strip()
            series_by_year.setdefault(y, []).append(s)
    return series_by_year


def load_postal_and_phone(csv_cp: str, csv_tlf: str) -> Tuple[Dict[str, List[str]], Dict[str, str], Dict[str, str]]:
    """Carga CP->municipios y prefijos de teléfono por provincia.
    Devuelve: (cp_to_municipalities, prov_to_tlf, prov_code_to_name)
    Lanza FileNotFoundError si faltan ficheros.
    """
    if not os.path.exists(csv_cp):
        raise FileNotFoundError(f"No se encontró el archivo requerido: {csv_cp}")
    if not os.path.exists(csv_tlf):
        raise FileNotFoundError(f"No se encontró el archivo requerido: {csv_tlf}")

    cp_to_municipalities: Dict[str, List[str]] = {}
    prov_to_tlf: Dict[str, str] = {}
    prov_code_to_name: Dict[str, str] = {}

    with open(csv_cp, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cp = row['codigo_postal'].zfill(5)
            municipio = row['municipio_nombre'].strip()
            cp_to_municipalities.setdefault(cp, []).append(municipio)

    with open(csv_tlf, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            prov_cp = row['postal_code'].zfill(2)
            prov_name = row['name'].strip()
            phone_code = row['phone_code'].strip()
            prov_to_tlf[prov_cp] = phone_code
            prov_code_to_name[prov_cp] = prov_name

    return cp_to_municipalities, prov_to_tlf, prov_code_to_name


# ===================== Writers (salida de datos) =====================

def write_csv(data: List[dict], filepath: str) -> None:
    if not data:
        return
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        w.writeheader()
        for row in data:
            w.writerow(row)


def write_parquet(data: List[dict], filepath: str) -> None:
    if not data:
        return
    if pa is None or pq is None:
        print(f"pyarrow no está instalado. Omitiendo Parquet: {filepath}")
        return
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    table = pa.Table.from_pylist(data)
    pq.write_table(table, filepath, compression='snappy')


def write_json_nested(users: List[dict], vehicles: List[dict], filepath: str) -> None:
    # Agrupar vehículos por DNI del propietario (acepta OwnerDNI o UserDNI)
    veh_by_dni: Dict[str, List[dict]] = {}
    for v in vehicles:
        key = v.get('OwnerDNI', v.get('UserDNI'))
        if key is not None:
            veh_by_dni.setdefault(key, []).append(v)

    users_nested = []
    for u in users:
        u_copy = dict(u)
        u_copy['Vehicles'] = veh_by_dni.get(u['DNI'], [])
        users_nested.append(u_copy)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(users_nested, f, ensure_ascii=False, indent=2)


def write_json_separated(users: List[dict], vehicles: List[dict], users_path: str, vehicles_path: str) -> None:
    os.makedirs(os.path.dirname(users_path), exist_ok=True)
    os.makedirs(os.path.dirname(vehicles_path), exist_ok=True)
    with open(users_path, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    with open(vehicles_path, 'w', encoding='utf-8') as f:
        json.dump(vehicles, f, ensure_ascii=False, indent=2)


def write_avro_nested(users: List[dict], vehicles: List[dict], filepath: str) -> None:
    if avro_writer is None or parse_schema is None:
        print(f"fastavro no está instalado. Omitiendo AVRO: {filepath}")
        return
    # Normalizar vehicles para usar siempre 'UserDNI' internamente
    vehicles_norm: List[dict] = []
    for v in vehicles:
        vd = dict(v)
        if 'OwnerDNI' in vd and 'UserDNI' not in vd:
            vd['UserDNI'] = vd.pop('OwnerDNI')
        vehicles_norm.append(vd)

    veh_by_dni: Dict[str, List[dict]] = {}
    for v in vehicles_norm:
        veh_by_dni.setdefault(v['UserDNI'], []).append(v)

    users_nested = []
    for u in users:
        u_copy = dict(u)
        u_copy['Vehicles'] = veh_by_dni.get(u['DNI'], [])
        users_nested.append(u_copy)

    schema = {
        "type": "record",
        "name": "User",
        "fields": [
            {"name": "Name", "type": "string"},
            {"name": "DNI", "type": "string"},
            {"name": "Email", "type": "string"},
            {"name": "PhoneMobile", "type": "string"},
            {"name": "PhoneLandline", "type": "string"},
            {"name": "Address", "type": "string"},
            {"name": "City", "type": "string"},
            {"name": "PostalCode", "type": "string"},
            {"name": "Province", "type": "string"},
            {"name": "Vehicles",
             "type": {
                 "type": "array",
                 "items": {
                     "type": "record",
                     "name": "Vehicle",
                     "fields": [
                         {"name": "Plate", "type": "string"},
                         {"name": "VIN", "type": "string"},
                         {"name": "Year", "type": "int"},
                         {"name": "Make", "type": "string"},
                         {"name": "Model", "type": "string"},
                         {"name": "Category", "type": "string"},
                         {"name": "UserDNI", "type": "string"}
                     ]
                 }
             }
            }
        ]
    }

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'wb') as out:
        avro_writer(out, parse_schema(schema), users_nested)


def write_avro_separated(users: List[dict], vehicles: List[dict], users_path: str, vehicles_path: str) -> None:
    if avro_writer is None or parse_schema is None:
        print(f"fastavro no está instalado. Omitiendo AVRO: {users_path}, {vehicles_path}")
        return
    user_schema = {
        "type": "record",
        "name": "User",
        "fields": [
            {"name": "Name", "type": "string"},
            {"name": "DNI", "type": "string"},
            {"name": "Email", "type": "string"},
            {"name": "PhoneMobile", "type": "string"},
            {"name": "PhoneLandline", "type": "string"},
            {"name": "Address", "type": "string"},
            {"name": "City", "type": "string"},
            {"name": "PostalCode", "type": "string"},
            {"name": "Province", "type": "string"}
        ]
    }

    vehicle_schema = {
        "type": "record",
        "name": "Vehicle",
        "fields": [
            {"name": "Plate", "type": "string"},
            {"name": "VIN", "type": "string"},
            {"name": "Year", "type": "int"},
            {"name": "Make", "type": "string"},
            {"name": "Model", "type": "string"},
            {"name": "Category", "type": "string"},
            {"name": "UserDNI", "type": "string"}
        ]
    }

    os.makedirs(os.path.dirname(users_path), exist_ok=True)
    os.makedirs(os.path.dirname(vehicles_path), exist_ok=True)
    with open(users_path, 'wb') as out:
        avro_writer(out, parse_schema(user_schema), users)

    # Normalizar vehicles a 'UserDNI' si vienen con 'OwnerDNI'
    vehicles_norm: List[dict] = []
    for v in vehicles:
        vd = dict(v)
        if 'OwnerDNI' in vd and 'UserDNI' not in vd:
            vd['UserDNI'] = vd.pop('OwnerDNI')
        vehicles_norm.append(vd)

    with open(vehicles_path, 'wb') as out:
        avro_writer(out, parse_schema(vehicle_schema), vehicles_norm)


def write_sqlite(users: List[dict], vehicles: List[dict], dbfile: str) -> None:
    os.makedirs(os.path.dirname(dbfile), exist_ok=True)
    con = sqlite3.connect(dbfile)
    try:
        cur = con.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")
        cur.execute("DROP TABLE IF EXISTS vehicles")
        cur.execute("DROP TABLE IF EXISTS users")
        cur.execute(
            """CREATE TABLE users (
                Name TEXT, DNI TEXT PRIMARY KEY, Email TEXT,
                PhoneMobile TEXT, PhoneLandline TEXT, Address TEXT,
                City TEXT, PostalCode TEXT, Province TEXT
            )"""
        )
        cur.execute(
            """CREATE TABLE vehicles (
                Plate TEXT PRIMARY KEY, VIN TEXT, Year INTEGER,
                Make TEXT, Model TEXT, Category TEXT, OwnerDNI TEXT,
                FOREIGN KEY (OwnerDNI) REFERENCES users(DNI)
            )"""
        )
        if users:
            usr_rows = [
                (
                    u['Name'], u['DNI'], u['Email'], u['PhoneMobile'], u['PhoneLandline'],
                    u['Address'], u['City'], u['PostalCode'], u['Province']
                ) for u in users
            ]
            cur.executemany("INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)", usr_rows)
        if vehicles:
            veh_rows = []
            for v in vehicles:
                owner = v.get('OwnerDNI', v.get('UserDNI'))
                veh_rows.append((
                    v['Plate'], v['VIN'], v['Year'], v['Make'], v['Model'], v['Category'], owner
                ))
            cur.executemany("INSERT INTO vehicles VALUES (?,?,?,?,?,?,?)", veh_rows)
        con.commit()
    finally:
        con.close()