import csv
import pyarrow as pa
import pyarrow.parquet as pq
import json
from fastavro import writer, parse_schema
import sqlite3

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


def write_json_nested(users, vehicles, filepath):
    veh_by_dni = {}
    for v in vehicles:
        veh_by_dni.setdefault(v["UserDNI"], []).append(v)
    # Añadir vehículos a cada usuario
    users_nested = []
    for u in users:
        u_copy = u.copy()
        u_copy["Vehicles"] = veh_by_dni.get(u["DNI"], [])
        users_nested.append(u_copy)
        
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(users_nested, f, ensure_ascii=False, indent=2)

def write_json_separated(users, vehicles, users_path, vehicles_path):
    with open(users_path, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    with open(vehicles_path, "w", encoding="utf-8") as f:
        json.dump(vehicles, f, ensure_ascii=False, indent=2)


def write_avro_nested(users, vehicles, filepath):
    # Preparamos los vehículos agrupados por DNI
    veh_by_dni = {}
    for v in vehicles:
        veh_by_dni.setdefault(v["UserDNI"], []).append(v)

    # Creamos los usuarios anidados
    users_nested = []
    for u in users:
        u_copy = u.copy()
        u_copy["Vehicles"] = veh_by_dni.get(u["DNI"], [])
        users_nested.append(u_copy)

    # Definir esquema Avro (anidado)
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

    parsed_schema = parse_schema(schema)
    with open(filepath, "wb") as out:
        writer(out, parsed_schema, users_nested)


def write_avro_separated(users, vehicles, users_path, vehicles_path):
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

    with open(users_path, "wb") as out:
        writer(out, parse_schema(user_schema), users)

    with open(vehicles_path, "wb") as out:
        writer(out, parse_schema(vehicle_schema), vehicles)


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