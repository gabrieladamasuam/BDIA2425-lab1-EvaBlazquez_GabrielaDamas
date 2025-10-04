from fastavro import reader
import sys

def read_avro(filepath, n=5):
    with open(filepath, "rb") as fo:
        avro_reader = reader(fo)
        print(f"\n📂 {filepath}")
        print("Schema:", avro_reader.writer_schema)
        print("Primeros registros:")
        for i, record in enumerate(avro_reader):
            print(record)
            if i >= n-1:
                break

if __name__ == "__main__":
    files = sys.argv[1:]
    if not files:
        print("Uso: python check_avro.py <ficheros.avro>")
    else:
        for f in files:
            read_avro(f, n=5)
