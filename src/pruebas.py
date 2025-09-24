import os
import argparse
import csv
from faker import Faker
from faker.providers import BaseProvider
from tqdm import tqdm
import random
import unicodedata

# -------------------------
# Cargar datos de códigos postales y prefijos de teléfono
# -------------------------
def load_postal_and_phone(csv_cp='codigos_postales_municipios.csv', csv_tlf='prov_tlf.csv'):
    cp_to_municipalities = {}
    prov_to_tlf = {}
    prov_code_to_name = {}

    # Cargar códigos postales y municipios
    try:
        with open(csv_cp, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cp = row['codigo_postal'].zfill(5)
                municipio = row['municipio_nombre'].strip()
                cp_to_municipalities.setdefault(cp, []).append(municipio)
        print(f"Cargados {len(cp_to_municipalities)} códigos postales únicos")
    except FileNotFoundError:
        print(f"⚠️ No se encontró el archivo {csv_cp}, usando fallback aleatorio")
        cp_to_municipalities = {}

    # Cargar prefijos de teléfono por provincia (indexados por código CP inicial)
    try:
        with open(csv_tlf, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                prov_cp = row['postal_code'].zfill(2)   # <-- columna con prefijo CP
                prov_name = row['name'].strip()               # nombre de provincia
                phone_code = row['phone_code'].strip()        # prefijo de teléfono
                prov_to_tlf[prov_cp] = phone_code
                prov_code_to_name[prov_cp] = prov_name
    except FileNotFoundError:
        print(f"⚠️ No se encontró el archivo {csv_tlf}, usando fallback aleatorio")
        prov_to_tlf = {}
        prov_code_to_name = {}

    return cp_to_municipalities, prov_to_tlf, prov_code_to_name


# -------------------------
# Provider de DNI
# -------------------------
class DNIProvider(BaseProvider):
    __letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
    def dni_number(self) -> int:
        return self.generator.random_int(min=11111111, max=99999999)
    def dni_control_letter(self, num: int) -> str:
        return self.__letters[num % 23]
    def dni(self) -> str:
        n = self.dni_number()
        return f"{n:08d}-{self.dni_control_letter(n)}"


# -------------------------
# Generadores
# -------------------------
def build_generators(seed=None, locale='es_ES'):
    fake = Faker(locale)
    if seed is not None:
        Faker.seed(seed)
        random.seed(seed)
    fake.add_provider(DNIProvider)
    return fake


def generate_users(fake, cp_to_municipalities, prov_to_tlf, prov_code_to_name, n):
    users = []
    landline_prob = 0.539  # Probabilidad de que la persona tenga teléfono fijo

    emails_generados = set()
    landlines_generados = set()

    if cp_to_municipalities:
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
    else:
        # Fallback si no hay CSV
        for _ in tqdm(range(n), desc="Generando usuarios aleatorios (sin CSV)"):
            dni = fake.unique.dni()
            phone_mobile = fake.unique.phone_number()
            cp = f"{random.randint(1000, 52999):05d}"
            municipio = f"Municipio-{cp}"

            phone_landline = fake.phone_number() if random.random() < landline_prob else ""

            users.append({
                "Name": fake.name(),
                "DNI": dni,
                "Email": fake.ascii_company_email(),
                "PhoneMobile": phone_mobile,
                "PhoneLandline": phone_landline,
                "Address": fake.street_address(),
                "City": municipio,
                "PostalCode": cp,
                "Province": "Desconocida"
            })

    return users


# -------------------------
# Escritura CSV
# -------------------------
def write_csv(data, filepath):
    if not data:
        return
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(list(data[0].keys()))
        for row in data:
            writer.writerow([row.get(k, "") for k in row.keys()])


# -------------------------
# CLI principal
# -------------------------
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

    users_csv = os.path.join(args.out_dir, "users.csv")
    write_csv(users, users_csv)
    print(f"Wrote CSV to {users_csv}")


if __name__ == "__main__":
    main()
