import os
import requests
import json
from datetime import datetime
import time

class DataQuery:
    def __init__(self, endpoint_url=None, save_folder='/app/data'):
        self.endpoint_url = endpoint_url or os.getenv("ENDPOINT_URL")
        self.save_folder = save_folder
        self.create_save_folder()  # Crear la carpeta de guardado al inicializar la instancia

    def create_save_folder(self):
        if not os.path.exists(self.save_folder):
            try:
                os.makedirs(self.save_folder)
                print(f"Carpeta de guardado '{self.save_folder}' creada exitosamente.")
            except OSError as e:
                print(f"No se pudo crear la carpeta de guardado: {e}")

    def fetch_data(self):
        try:
            response = requests.get(self.endpoint_url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error al obtener los datos: {e}")
            return None

    def generate_filename(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.save_folder}/{timestamp}.json"

    def save_data(self, data):
        filename = self.generate_filename()
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"Datos guardados correctamente en '{filename}'")
        except IOError as e:
            print(f"Error al guardar los datos: {e}")

def main():
    query = DataQuery()
    minutes = os.getenv('minutes', 5)
    minutes = int(minutes)
    while True:
        data = query.fetch_data()

        if data:
            query.save_data(data)

        time.sleep(minutes*60)
    pass

if __name__ == "__main__":
    main()
    