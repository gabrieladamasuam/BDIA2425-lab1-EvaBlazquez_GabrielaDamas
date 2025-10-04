import psycopg2

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
