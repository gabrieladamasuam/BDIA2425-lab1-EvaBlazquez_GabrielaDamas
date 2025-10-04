import psycopg2
import os
import sqlite3

def get_connection(db_config):
    return psycopg2.connect(
        dbname=db_config['dbname'],
        user=db_config['user'],
        password=db_config['password'],
        host=db_config['host'],
        port=db_config['port']
    )

def create_tables(db_config):
    conn = get_connection(db_config)
    cur = conn.cursor()
    
    # Tabla usuarios
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        dni VARCHAR(10) PRIMARY KEY,
        name VARCHAR(100),
        email VARCHAR(100),
        phone_mobile VARCHAR(20),
        phone_landline VARCHAR(20),
        address TEXT,
        city VARCHAR(50),
        postal_code VARCHAR(10),
        province VARCHAR(50)
    );
    """)

    # Tabla vehículos
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        plate VARCHAR(10) PRIMARY KEY,
        vin VARCHAR(20),
        year INT,
        make VARCHAR(50),
        model VARCHAR(50),
        category VARCHAR(50),
        user_dni VARCHAR(10) REFERENCES users(dni)
    );
    """)

    conn.commit()
    cur.close()
    conn.close()


def insert_into_postgres(users, vehicles, db_config):
    conn = get_connection(db_config)
    cur = conn.cursor()
    
    # Insertar usuarios
    for u in users:
        cur.execute("""
        INSERT INTO users(dni, name, email, phone_mobile, phone_landline, address, city, postal_code, province)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (dni) DO NOTHING;
        """, (u['DNI'], u['Name'], u['Email'], u['PhoneMobile'], u['PhoneLandline'], u['Address'], u['City'], u['PostalCode'], u['Province']))
    
    # Insertar vehículos
    for v in vehicles:
        cur.execute("""
        INSERT INTO vehicles(plate, vin, year, make, model, category, user_dni)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (plate) DO NOTHING;
        """, (v['Plate'], v['VIN'], v['Year'], v['Make'], v['Model'], v['Category'], v['UserDNI']))
    
    conn.commit()
    cur.close()
    conn.close()


def write_sqlite(users, vehicles, dbfile):
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
                Make TEXT, Model TEXT, Category TEXT, UserDNI TEXT,
                FOREIGN KEY (UserDNI) REFERENCES users(DNI)
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
            veh_rows = [
                (
                    v['Plate'], v['VIN'], v['Year'], v['Make'], v['Model'], v['Category'], v['UserDNI']
                ) for v in vehicles
            ]
            cur.executemany("INSERT INTO vehicles VALUES (?,?,?,?,?,?,?)", veh_rows)
        con.commit()
    finally:
        con.close()
