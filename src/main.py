import os
import argparse
from generators import build_generators, generate_users, generate_vehicles
from io_utils import write_csv, write_parquet, write_json_nested, write_json_separated, write_avro_nested, write_avro_separated
from db_utils import write_sqlite, create_tables, insert_into_postgres, insert_into_mongodb, ensure_database_exists, truncate_postgres_tables


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_users", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=None)

    # Parámetros opcionales para PostgreSQL (sobrescriben variables de entorno si se proporcionan)
    parser.add_argument("--pg-dbname", type=str, help="Nombre de la base de datos de PostgreSQL")
    parser.add_argument("--pg-user", type=str, help="Usuario de PostgreSQL")
    parser.add_argument("--pg-password", type=str, help="Contraseña de PostgreSQL")
    parser.add_argument("--pg-host", type=str, help="Host de PostgreSQL")
    parser.add_argument("--pg-port", type=int, help="Puerto de PostgreSQL")
    parser.add_argument("--pg-create-db", action="store_true", help="Crear la base de datos destino si no existe (requiere privilegios)")
    parser.add_argument("--pg-admin-db", type=str, default="postgres", help="Base de datos administrativa para crear la BD destino (por defecto: postgres)")
    parser.add_argument("--pg-reset", action="store_true", help="Vaciar tablas (TRUNCATE) antes de insertar para no acumular entre ejecuciones")

    # Parámetros opcionales para MongoDB
    parser.add_argument("--mongo-uri", type=str, help="Cadena de conexión de MongoDB (por defecto MONGO_URI o mongodb://localhost:27017/)")
    parser.add_argument("--mongo-db", type=str, help="Nombre de la base de datos de MongoDB (por defecto: usuarios_vehiculos)")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    out_dir = os.path.join(repo_root, "output")
    os.makedirs(out_dir, exist_ok=True)

    # Configuración de PostgreSQL: variables de entorno con override por flags
    db_config = {
        "dbname": os.environ.get("POSTGRES_DB", "usuarios_vehiculos"),
        "user": os.environ.get("POSTGRES_USER", "postgres"),
        "password": os.environ.get("POSTGRES_PASSWORD", "1234"),
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    }
    if args.pg_dbname: db_config["dbname"] = args.pg_dbname
    if args.pg_user: db_config["user"] = args.pg_user
    if args.pg_password: db_config["password"] = args.pg_password
    if args.pg_host: db_config["host"] = args.pg_host
    if args.pg_port: db_config["port"] = args.pg_port

    # Resumen de ejecución
    print(f"Iniciando generación: n_users={args.n_users}, seed={args.seed}, out_dir={out_dir}")
    pg_dest = f"{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
    print(f"Destino PostgreSQL: {pg_dest}")

    # Configuración MongoDB
    mongo_uri = args.mongo_uri or os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    mongo_db = args.mongo_db or os.environ.get("MONGO_DB", "usuarios_vehiculos")
    print(f"Destino MongoDB: {mongo_uri} db={mongo_db}")

    fake = build_generators(seed=args.seed)
    users = generate_users(fake, args.n_users)
    vehicles = generate_vehicles(fake, users)
    
    # CSV
    users_csv = os.path.join(out_dir, "users.csv")
    vehicles_csv = os.path.join(out_dir, "vehicles.csv")
    write_csv(users, users_csv)
    write_csv(vehicles, vehicles_csv)

    # Parquet
    users_parquet = os.path.join(out_dir, "users.parquet")
    vehicles_parquet = os.path.join(out_dir, "vehicles.parquet")
    write_parquet(users, users_parquet)
    write_parquet(vehicles, vehicles_parquet)
    
    # JSON
    json_nested_path = os.path.join(out_dir, "users_nested.json")
    users_json_path = os.path.join(out_dir, "users.json")
    vehicles_json_path = os.path.join(out_dir, "vehicles.json")
    write_json_nested(users, vehicles, json_nested_path)
    write_json_separated(users, vehicles, users_json_path, vehicles_json_path)
    
    # AVRO
    users_avro_nested = os.path.join(out_dir, "users_nested.avro")
    users_avro_path = os.path.join(out_dir, "users.avro")
    vehicles_avro_path = os.path.join(out_dir, "vehicles.avro")
    write_avro_nested(users, vehicles, users_avro_nested)
    write_avro_separated(users, vehicles, users_avro_path, vehicles_avro_path)

    # SQLite
    sqlite_file = os.path.join(out_dir, "fake_data.sqlite3")
    write_sqlite(users, vehicles, sqlite_file)
    
    # PostgreSQL
    postgres_ok = False
    try:
        if args.pg_create_db:
            try:
                ensure_database_exists(db_config, admin_db=args.pg_admin_db)
            except Exception as e:
                print(f"PostgreSQL: no se pudo asegurar la BD '{db_config['dbname']}' (creación opcional): {e}")
        create_tables(db_config)
        if args.pg_reset:
            try:
                truncate_postgres_tables(db_config)
            except Exception as e:
                print(f"PostgreSQL: no se pudieron truncar las tablas: {e}")
        insert_into_postgres(users, vehicles, db_config)
        postgres_ok = True
    except Exception as e:
        print(f"PostgreSQL: error al crear/insertar: {e}")

    # MongoDB
    mongodb_ok = False
    try:
        insert_into_mongodb(users, vehicles, db_name=mongo_db, uri=mongo_uri)
        mongodb_ok = True
    except Exception as e:
        print(f"MongoDB: error al insertar: {e}")
    
    print("Proceso completado.")

if __name__ == "__main__":
    main()
        
