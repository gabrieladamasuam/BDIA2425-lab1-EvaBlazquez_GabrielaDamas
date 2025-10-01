import os
import argparse
import csv
from faker import Faker
from faker.providers import BaseProvider
from tqdm import tqdm
import random
import unicodedata

# Cargar datos de códigos postales y prefijos de teléfono
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
        print(f"No se encontró el archivo {csv_cp}, usando fallback aleatorio")
        cp_to_municipalities = {}
    # Cargar prefijos de teléfono por provincia (indexados por código CP inicial)
    try:
        with open(csv_tlf, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                prov_cp = row['postal_code'].zfill(2)   # columna con prefijo CP
                prov_name = row['name'].strip()         # nombre de provincia
                phone_code = row['phone_code'].strip()  # prefijo de teléfono
                prov_to_tlf[prov_cp] = phone_code
                prov_code_to_name[prov_cp] = prov_name
    except FileNotFoundError:
        print(f"No se encontró el archivo {csv_tlf}, usando fallback aleatorio")
        prov_to_tlf = {}
        prov_code_to_name = {}

    return cp_to_municipalities, prov_to_tlf, prov_code_to_name

# Provider de DNI
class DNIProvider(BaseProvider):
    __letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
    def dni_number(self) -> int:
        return self.generator.random_int(min=11111111, max=99999999)
    def dni_control_letter(self, num: int) -> str:
        return self.__letters[num % 23]
    def dni(self) -> str:
        n = self.dni_number()
        return f"{n:08d}-{self.dni_control_letter(n)}"

###################################################################################
SERIES_MATRICULAS = {
    2000: ["BBJ","BCD","BCY","BDR"],
    2001: ["BFJ","BGF","BHG","BJC","BKB","BLC","BMF","BMW","BNL","BPG","BRB","BRT"],
    2002: ["BSL","BTF","BTZ","BVW","BWT","BXP","BYP","BZF","BZV","CBP","CCH","CDC"],
    2003: ["CDV","CFM","CGJ","CHF","CJC","CKB","CLD","CLV","CMM","CNK","CPF","CRC"],
    2004: ["CRV","CSS","CTT","CVR","CWR","CXT","CYY","CZP","DBJ","DCH","DDG","DFF"],
    2005: ["DFZ","DGX","DHZ","DKB","DLD","DMJ","DNP","DPK","DRG","DSC","DTB","DVB"],
    2006: ["DVW","DWT","DXZ","DYY","FBC","FCJ","FDP","FFK","FGF","FHD","FJD","FKC"],
    2007: ["FKY","FLV","FNB","FNZ","FRC","FSJ","FTP","FVJ","FWC","FXB","FXY","FYY"],
    2008: ["FZR","GBN","GCK","GDH","GFC","GFY","GGV","GHG","GHT","GJJ","GJV","GKH"],
    2009: ["GKS","GLC","GLP","GMC","GMN","GNF","GNY","GPJ","GPW","GRM","GSC","GSR"],
    2010: ["GTC","GTS","GVM","GWC","GWV","GXP","GYD","GYM","GYX","GZJ","GZT","HBG"],
    2011: ["HBP","HCB","HCR","HDC","HDR","HFF","HFT","HGC","HGM","HGX","HHH","HHT"],
    2012: ["HJC","HJM","HKB","HKL","HKX","HLK","HLW","HMD","HML","HMT","HNC","HNK"],
    2013: ["HNT","HPC","HPN","HPY","HRK","HRX","HSK","HSR","HSZ","HTK","HTV","HVF"],
    2014: ["HVN","HVZ","HWM","HWY","HXN","HYD","HYT","HZB","HZL","HZZ","JBL","JBY"],
    2015: ["JCK","JCY","JDR","JFG","JFX","JGR","JHJ","JHT","JJH","JJW","JKK","JKZ"],
    2016: ["JLN","JMF","JMY","JNR","JPK","JRG","JRZ","JSL","JTB","JTR","JVH","JVZ"],
    2017: ["JWN","JXF","JYB","JYT","JZP","KBM","KCH","KCV","KDK","KFC","KFW","KGN"],
    2018: ["KHG","KHY","KJV","KKR","KLN","KMM","KNK","KPD","KPS","KRJ","KRZ","KSS"],
    2019: ["KTJ","KVB","KVX","KWT","KXR","KYN","KZK","KZY","LBN","LCG","LCY","LDR"],
    2020: ["LFH","LFY","LGG","LGH","LGP","LHG","LJD","LJR","LKF","LKV","LLJ","LMC"],
    2021: ["LML","LMX","LNN","LPD","LPW","LRP","LSG","LSR","LTD","LTP","LVD","LVV"],
    2022: ["LWD","LWR","LXD","LXS","LYJ","LYZ","LZP","LZZ","MBN","MCB","MCR","MDF"],
    2023: ["MDS","MFG","MFZ","MGN","MHG","MJB","MJR","MKD","MKR","MLH","MLY","MMN"],
    2024: ["MNC","MNT","MPL","MRD","MRX","MSS","MTK","MTW","MVL","MWD","MWV","MXP"],
    2025: ["MYF","MYW","MZS","NBL","NCJ","NDG","NFC","NFR","NGB"],
}

class PlateProvider(BaseProvider):
    def plate(self, year: int = None) -> str:
        if year is None:
            year = random.randint(2000, 2025)
        series = SERIES_MATRICULAS.get(year, ["ZZZ"])
        letters = random.choice(series)
        nums = random.randint(0, 9999)
        return f"{nums:04d}{letters}"

MANUFACTURERS = [
    {"make": "Seat", "wmi": "VSS"},
    {"make": "Volkswagen", "wmi": "WVW"},
    {"make": "Audi", "wmi": "WAU"},
    {"make": "BMW", "wmi": "WBA"},
    {"make": "Mercedes-Benz", "wmi": "WDB"},
    {"make": "Renault", "wmi": "VF1"},
    {"make": "Peugeot", "wmi": "VF3"},
    {"make": "Toyota", "wmi": "JT2"},
    {"make": "Ford", "wmi": "WF0"},
    {"make": "Citroën", "wmi": "VF7"}
]

class VINProvider(BaseProvider):
    chars = "0123456789ABCDEFGHJKLMNPRSTUVWXYZ"  # sin I, O, Q

    year_codes = {
        2000: "Y", 2001: "1", 2002: "2", 2003: "3", 2004: "4",
        2005: "5", 2006: "6", 2007: "7", 2008: "8", 2009: "9",
        2010: "A", 2011: "B", 2012: "C", 2013: "D", 2014: "E",
        2015: "F", 2016: "G", 2017: "H", 2018: "J", 2019: "K",
        2020: "L", 2021: "M", 2022: "N", 2023: "P", 2024: "R",
        2025: "S"
    }

    transl = {
        **{str(i): i for i in range(10)},
        **dict(zip("ABCDEFGHJKLMNPRSTUVWXYZ", 
                   [1,2,3,4,5,6,7,8,1,2,3,4,5,6,7,8,9,2,3,4,5,6,7,8,9]))
    }
    
    weights = [8,7,6,5,4,3,2,10,0,9,8,7,6,5,4,3,2]

    def vin(self, wmi: str, year: int) -> str:
        # Generar VDS (4-8)
        vds = ''.join(random.choice(self.chars) for _ in range(5))
        
        # Año en el carácter 10
        year_char = self.year_codes.get(year, "X")
        
        # Planta de ensamblaje (11)
        plant = random.choice(self.chars)
        
        # Número de serie (12-17)
        serial = ''.join(random.choice(self.chars) for _ in range(6))
        
        # VIN provisional con dígito 9 temporal y luego lo sustituimos
        vin_temp = f"{wmi}{vds}0{year_char}{plant}{serial}"
        
        # Calcular checksum para el 9º carácter
        check_digit = self._calculate_checksum(vin_temp)
        
        # VIN final
        vin_final = f"{wmi}{vds}{check_digit}{year_char}{plant}{serial}"
        return vin_final

    def _calculate_checksum(self, vin17: str) -> str:
        total = 0
        for i, char in enumerate(vin17):
            val = self.transl.get(char, 0)
            total += val * self.weights[i]
        remainder = total % 11
        return "X" if remainder == 10 else str(remainder)
    

############################################################################### Generadores

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

VEHICLE_CATEGORIES = [
    "urbano", "sedán", "berlina", "cupé", "descapotable", "deportivo", 
    "todoterreno", "monovolumen", "SUV"
]

def generate_vehicles(fake, users, vehicles_per_user_avg=1.2):
    vehicles = []
    n_users = len(users)
    dnis = [u["DNI"] for u in users]
    expected_total = int(n_users * vehicles_per_user_avg)
    
    used_plates = set()
    used_vins = set()

    for _ in tqdm(range(expected_total), desc="Generando vehículos"):
        owner = random.choice(dnis)
        year = random.randint(2000, 2025)

        plate = fake.plate(year)
        while plate in used_plates:
            plate = fake.plate(year)
        used_plates.add(plate)

        manufacturer = random.choice(MANUFACTURERS)
        vin = fake.vin(manufacturer["wmi"], year)
        while vin in used_vins:
            vin = fake.vin(manufacturer["wmi"], year)
        used_vins.add(vin)

        veh = {
            "Plate": plate,
            "VIN": vin,
            "Year": year,
            "Make": manufacturer["make"],
            "Model": fake.word().title(),
            "Category": random.choice(VEHICLE_CATEGORIES),
            "OwnerDNI": owner
        }
        vehicles.append(veh)

    return vehicles

# Escritura CSV
def write_csv(data, filepath):
    if not data:
        return
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(list(data[0].keys()))
        for row in data:
            writer.writerow([row.get(k, "") for k in row.keys()])

# CLI principal
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