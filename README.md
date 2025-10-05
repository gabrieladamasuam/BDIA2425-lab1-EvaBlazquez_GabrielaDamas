# BDIA 24/25 · Práctica 1 — Generación de datos sintéticos

Este proyecto genera datos sintéticos de usuarios y vehículos y los exporta a varios formatos (CSV, Parquet, JSON, Avro), además de cargarlos en SQLite, PostgreSQL y MongoDB de forma opcional.

## Requisitos

- Python 3.10+ (recomendado)
- Dependencias Python:
  - faker, tqdm, pyarrow, fastavro, psycopg2-binary, pymongo
- Servicios opcionales (solo si quieres cargar BBDD):
  - PostgreSQL accesible (localhost:5432 por defecto)
  - MongoDB accesible (mongodb://localhost:27017/ por defecto)

Instalación de dependencias (una vez, dentro del repo):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Estructura relevante

- `src/main.py`: punto de entrada del programa
- `src/generators.py`: generadores de usuarios y vehículos
- `src/io_utils.py`: escritura de ficheros con barras de progreso
- `src/db_utils.py`: carga en SQLite, PostgreSQL y MongoDB (con barras)
- `data/`: ficheros de soporte
  - `codigos_postales_municipios.csv`
  - `prov_tlf.csv`
  - `series_matriculas.csv`
  - `models_by_make.csv`
- `output/`: se crea automáticamente con los ficheros generados

## Cómo ejecutar

Mínimo (genera 1000 usuarios, escribe ficheros y SQLite):

```bash
python3 src/main.py --seed 1 --n_users 1000
```

Parámetros principales:
- `--seed`: semilla para que la generación sea reproducible
- `--n_users`: número de usuarios (los vehículos se asignan probabilísticamente)

### Carga en PostgreSQL (opcional)

Configura por variables de entorno o por flags. Ejemplos:

- Usando flags y creando la BD si no existe:
```bash
python3 src/main.py \
  --seed 1 --n_users 1000 \
  --pg-dbname usuarios_vehiculos \
  --pg-user postgres --pg-password 1234 \
  --pg-host localhost --pg-port 5432 \
  --pg-create-db
```

- Evitar acumulación entre ejecuciones (TRUNCATE antes de insertar):
```bash
python3 src/main.py --seed 1 --n_users 1000 --pg-dbname usuarios_vehiculos --pg-reset
```

También puedes usar variables de entorno (se pueden mezclar con flags):

```bash
export POSTGRES_DB=usuarios_vehiculos
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=1234
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
python3 src/main.py --seed 1 --n_users 1000
```

### Carga en MongoDB (opcional)

Por defecto usa `mongodb://localhost:27017/` y BD `usuarios_vehiculos`. Puedes cambiarlo:

```bash
python3 src/main.py --seed 1 --n_users 1000 \
  --mongo-uri "mongodb://localhost:27017/" \
  --mongo-db usuarios_vehiculos
```

## Ficheros de salida

Se escriben en `output/`:
- `users.csv`, `vehicles.csv`
- `users.parquet`, `vehicles.parquet`
- `users.json`, `vehicles.json`
- `users_nested.json`
- `users.avro`, `vehicles.avro`
- `users_nested.avro`
- `fake_data.sqlite3` (SQLite)

Las barras de progreso se muestran solo durante la escritura y carga en BBDD (mensajes tipo “Escribiendo …”).

## Verificar conteos

- SQLite:
```bash
sqlite3 output/fake_data.sqlite3 'SELECT "users" AS tabla, COUNT(*) FROM users UNION ALL SELECT "vehicles", COUNT(*) FROM vehicles;'
```

- PostgreSQL:
```bash
psql -h localhost -p 5432 -U postgres -d usuarios_vehiculos \
  -c "SELECT 'users' AS tabla, COUNT(*) FROM users UNION ALL SELECT 'vehicles', COUNT(*) FROM vehicles;"
```

- MongoDB:
```bash
mongosh usuarios_vehiculos --quiet --eval 'db.users.countDocuments()'
mongosh usuarios_vehiculos --quiet --eval 'db.vehicles.countDocuments()'
# o en una sola línea con URI
mongosh "mongodb://localhost:27017/" --quiet --eval 'const d=db.getSiblingDB("usuarios_vehiculos"); printjson({users: d.users.countDocuments(), vehicles: d.vehicles.countDocuments()})'
```

## Notas y resolución de problemas

- Si falta alguna librería (p. ej., pyarrow o fastavro), instálala con `pip install -r requirements.txt`.
- PostgreSQL acumula entre ejecuciones si no usas `--pg-reset` (SQLite y Mongo se resetean cada vez).
- Puedes fijar valores por defecto con variables de entorno y así simplificar el comando.
- Si cambias `--seed` o `--n_users`, las matrículas/vins pueden variar (y aumentar el total en Postgres si no reseteas).

## Licencia

Proyecto académico para la asignatura BDIA 24/25.
