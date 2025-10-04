import os
import argparse
from generators import load_postal_and_phone, build_generators, generate_users, generate_vehicles
from io_utils import write_csv, write_parquet, write_json_nested, write_json_separated, write_avro_nested, write_avro_separated, write_sqlite
from db_utils import create_tables, insert_into_postgres 

    
db_config = {
"dbname": "postgres",  
"user": "postgres",
"password": "1234",
"host": "localhost",
"port": 5432
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_users", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--data_dir", type=str, default="../data")
    parser.add_argument("--out_dir", type=str, default="../output")
    args = parser.parse_args()

    cp_file = os.path.join(args.data_dir, "codigos_postales_municipios.csv")
    tlf_file = os.path.join(args.data_dir, "prov_tlf.csv")
    cp_to_municipalities, prov_to_tlf, prov_code_to_name = load_postal_and_phone(cp_file, tlf_file)
    os.makedirs(args.out_dir, exist_ok=True)

    fake = build_generators(seed=args.seed)
    users = generate_users(fake, cp_to_municipalities, prov_to_tlf, prov_code_to_name, args.n_users)
    vehicles = generate_vehicles(fake, users)
    
    # CSV
    users_csv = os.path.join(args.out_dir, "users.csv")
    vehicles_csv = os.path.join(args.out_dir, "vehicles.csv")
    write_csv(users, users_csv)
    write_csv(vehicles, vehicles_csv)

    # Parquet
    users_parquet = os.path.join(args.out_dir, "users.parquet")
    vehicles_parquet = os.path.join(args.out_dir, "vehicles.parquet")
    write_parquet(users, users_parquet)
    write_parquet(vehicles, vehicles_parquet)
    print(f"Wrote Parquet to {users_parquet}, {vehicles_parquet}")
    
    # JSON
    json_nested_path = os.path.join(args.out_dir, "users_nested.json")
    users_json_path = os.path.join(args.out_dir, "users.json")
    vehicles_json_path = os.path.join(args.out_dir, "vehicles.json")
    write_json_nested(users, vehicles, json_nested_path)
    write_json_separated(users, vehicles, users_json_path, vehicles_json_path)
    
    # AVRO
    users_avro_nested = os.path.join(args.out_dir, "users_nested.avro")
    users_avro_path = os.path.join(args.out_dir, "users.avro")
    vehicles_avro_path = os.path.join(args.out_dir, "vehicles.avro")
    write_avro_nested(users, vehicles, users_avro_nested)
    write_avro_separated(users, vehicles, users_avro_path, vehicles_avro_path)

    # SQLite
    sqlite_file = os.path.join(args.out_dir, "fake_data.sqlite3")
    write_sqlite(users, vehicles, sqlite_file)
    
    create_tables(db_config)
    insert_into_postgres(users, vehicles, db_config)
    
    print(f"Wrote CSV to {users_csv} y {vehicles_csv}")
    print(f"Wrote Parquet to {users_parquet} y {vehicles_parquet}")
    print(f"Wrote nested JSON to {json_nested_path}")
    print(f"Wrote users JSON to {users_json_path}")
    print(f"Wrote vehicles JSON to {vehicles_json_path}")
    print(f"Wrote nested AVRO to {users_avro_nested}")
    print(f"Wrote users AVRO to {users_avro_path}")
    print(f"Wrote vehicles AVRO to {vehicles_avro_path}") 
    print(f"Wrote SQLite DB to {sqlite_file}")
    print("Datos volcados a PostgreSQL correctamente.")
    print("Proceso completado.")

if __name__ == "__main__":
    main()
        
