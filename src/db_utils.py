import os
import sqlite3
import psycopg2
from psycopg2 import sql, errors
from pymongo import MongoClient
from tqdm import tqdm

# ============================= SQLite =============================
def write_sqlite(users, vehicles, dbfile, show_progress = True, batch_size = 10000):
    """Crea y rellena una BD SQLite; borra tablas, crea y hace inserciones por lotes."""
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
            pbar = tqdm(total=len(users), desc="Escribiendo SQLite usuarios", unit="fila") if show_progress else None
            for i in range(0, len(users), batch_size):
                chunk = users[i:i+batch_size]
                usr_rows = [
                    (
                        u['Name'], u['DNI'], u['Email'], u['PhoneMobile'], u['PhoneLandline'],
                        u['Address'], u['City'], u['PostalCode'], u['Province']
                    ) for u in chunk
                ]
                cur.executemany("INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?)", usr_rows)
                if pbar:
                    pbar.update(len(chunk))
            if pbar:
                pbar.close()
        if vehicles:
            pbar = tqdm(total=len(vehicles), desc="Escribiendo SQLite vehículos", unit="fila") if show_progress else None
            for i in range(0, len(vehicles), batch_size):
                chunk = vehicles[i:i+batch_size]
                veh_rows = [
                    (
                        v['Plate'], v['VIN'], v['Year'], v['Make'], v['Model'], v['Category'], v['UserDNI']
                    ) for v in chunk
                ]
                cur.executemany("INSERT INTO vehicles VALUES (?,?,?,?,?,?,?)", veh_rows)
                if pbar:
                    pbar.update(len(chunk))
            if pbar:
                pbar.close()
        con.commit()
    finally:
        con.close()

# ============================= PostgreSQL =============================
def get_connection(db_config):
    """Devuelve una conexión a PostgreSQL usando db_config."""
    return psycopg2.connect(
        dbname=db_config['dbname'],
        user=db_config['user'],
        password=db_config['password'],
        host=db_config['host'],
        port=db_config['port']
    )

def ensure_database_exists(db_config, admin_db = "postgres"):
    """Crea la base de datos si no existe conectando a admin_db (requiere permisos)."""
    # Conectar a la BD administrativa con las mismas credenciales
    conn = psycopg2.connect(
        dbname=admin_db,
        user=db_config['user'],
        password=db_config['password'],
        host=db_config['host'],
        port=db_config['port']
    )
    try:
        # CREATE DATABASE no puede ejecutarse dentro de una transacción
        conn.autocommit = True
        with conn.cursor() as cur:
            try:
                cur.execute(sql.SQL("CREATE DATABASE {}")
                            .format(sql.Identifier(db_config['dbname'])))
            except errors.DuplicateDatabase:
                # Ya existe, no hacer nada
                pass
    finally:
        conn.close()

def create_tables(db_config):
    """Crea tablas users y vehicles en PostgreSQL si no existen."""
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

def truncate_postgres_tables(db_config):
    """Vacía tablas vehicles y users en una sola instrucción TRUNCATE."""
    conn = get_connection(db_config)
    try:
        with conn.cursor() as cur:
            # Truncar ambas tablas en una sola sentencia evita problemas de ForeignKey entre ellas.
            cur.execute("TRUNCATE TABLE vehicles, users;")
        conn.commit()
    finally:
        conn.close()

def insert_into_postgres(users, vehicles, db_config, show_progress = True):
    """Inserta users y vehicles en PostgreSQL con ON CONFLICT DO NOTHING y progreso."""
    conn = get_connection(db_config)
    cur = conn.cursor()
    # ON CONFLICT DO NOTHING: evita duplicados; para reset usa --pg-reset; para upsert cambia a DO UPDATE.
    # Insertar usuarios
    user_iter = tqdm(users, desc="Escribiendo PostgreSQL usuarios", unit="fila") if show_progress else users
    for u in user_iter:
        cur.execute("""
        INSERT INTO users(dni, name, email, phone_mobile, phone_landline, address, city, postal_code, province)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (dni) DO NOTHING;
        """, (u['DNI'], u['Name'], u['Email'], u['PhoneMobile'], u['PhoneLandline'], u['Address'], u['City'], u['PostalCode'], u['Province']))
    # Insertar vehículos
    veh_iter = tqdm(vehicles, desc="Escribiendo PostgreSQL vehículos", unit="fila") if show_progress else vehicles
    for v in veh_iter:
        cur.execute("""
        INSERT INTO vehicles(plate, vin, year, make, model, category, user_dni)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (plate) DO NOTHING;
        """, (v['Plate'], v['VIN'], v['Year'], v['Make'], v['Model'], v['Category'], v['UserDNI']))
    conn.commit()
    cur.close()
    conn.close()

# ============================= MongoDB =============================
def get_mongo_client(uri="mongodb://localhost:27017/"):
    """Devuelve un cliente de MongoDB para la URI dada."""
    client = MongoClient(uri)
    return client

def insert_into_mongodb(users, vehicles, db_name="usuarios_vehiculos", uri = None, show_progress = True, batch_size = 50000):
    """Vacía e inserta users y vehicles en MongoDB por lotes con barra de progreso."""
    client = get_mongo_client(uri or "mongodb://localhost:27017/")
    db = client[db_name]
    
    # Colecciones
    users_col = db["users"]
    vehicles_col = db["vehicles"]
    
    # Limpiar colecciones existentes
    users_col.delete_many({})
    vehicles_col.delete_many({})

    # Insertar datos (posible chunking para grandes volúmenes)
    if users:
        pbar = tqdm(total=len(users), desc="Escribiendo MongoDB usuarios", unit="fila") if show_progress else None
        for i in range(0, len(users), batch_size):
            chunk = users[i:i+batch_size]
            users_col.insert_many(chunk)
            if pbar:
                pbar.update(len(chunk))
        if pbar:
            pbar.close()

    if vehicles:
        pbar = tqdm(total=len(vehicles), desc="Escribiendo MongoDB vehículos", unit="fila") if show_progress else None
        for i in range(0, len(vehicles), batch_size):
            chunk = vehicles[i:i+batch_size]
            vehicles_col.insert_many(chunk)
            if pbar:
                pbar.update(len(chunk))
        if pbar:
            pbar.close()

    client.close()
