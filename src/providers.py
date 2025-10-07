from faker.providers import BaseProvider
import random
import os
from io_utils import load_plate_series


class DNIProvider(BaseProvider):
    """Genera DNI válidos (8 dígitos + letra de control oficial)."""
    __letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
    def dni_number(self) -> int:
        return self.generator.random_int(min=11111111, max=99999999)
    def dni_control_letter(self, num: int) -> str:
        return self.__letters[num % 23]
    def dni(self) -> str:
        n = self.dni_number()
        return f"{n:08d}-{self.dni_control_letter(n)}"



_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
_SERIES_FILE = os.path.join(_REPO_ROOT, 'data', 'series_matriculas.csv')


class PlateProvider(BaseProvider):
    """Genera matrículas españolas usando series por año cargadas desde CSV."""
    series_by_year = load_plate_series(_SERIES_FILE)
    min_year = min(series_by_year.keys()) if series_by_year else 2000
    max_year = max(series_by_year.keys()) if series_by_year else 2025

    def plate(self, year: int = None) -> str:
        """Devuelve una matrícula (NNNN-LLL) coherente con el año proporcionado."""
        if year is None:
            year = random.randint(self.min_year, self.max_year)
        series = self.series_by_year.get(year, ["ZZZ"])
        letters = random.choice(series)
        nums = random.randint(0, 9999)
        return f"{nums:04d}{letters}"



class VINProvider(BaseProvider):
    """Genera VIN de 17 caracteres con checksum y codificación de año."""
    chars = "0123456789ABCDEFGHJKLMNPRSTUVWXYZ"  # sin I, O, Q

    # Códigos de año cubiertos 2000–2025; si el año no existe en el mapa se usa 'X'
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
        """Devuelve un VIN válido combinando WMI, año y dígito de control."""
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
        """Calcula el dígito de control (posición 9) del VIN."""
        total = 0
        for i, char in enumerate(vin17):
            val = self.transl.get(char, 0)
            total += val * self.weights[i]
        remainder = total % 11
        return "X" if remainder == 10 else str(remainder)