from faker.providers import BaseProvider
import random


class DNIProvider(BaseProvider):
    __letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
    def dni_number(self) -> int:
        return self.generator.random_int(min=11111111, max=99999999)
    def dni_control_letter(self, num: int) -> str:
        return self.__letters[num % 23]
    def dni(self) -> str:
        n = self.dni_number()
        return f"{n:08d}-{self.dni_control_letter(n)}"



class PlateProvider(BaseProvider):
    def __init__(self, generator, series_by_year):
        super().__init__(generator)
        self.series_by_year = series_by_year
        self.min_year = min(series_by_year.keys()) if series_by_year else 2000
        self.max_year = max(series_by_year.keys()) if series_by_year else 2025

    def plate(self, year: int = None) -> str:
        if year is None:
            year = random.randint(self.min_year, self.max_year)
        series = self.series_by_year.get(year, ["ZZZ"])
        letters = random.choice(series)
        nums = random.randint(0, 9999)
        return f"{nums:04d}{letters}"



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