import os
import requests
import json
from datetime import datetime
import time
import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine
import redis
import warnings

# Ignorar todas las advertencias
warnings.filterwarnings("ignore")

class DataExtractor:
    def __init__(self, endpoint_url=None, save_folder='/app/data'):
        self.endpoint_url = endpoint_url or os.getenv("ENDPOINT_URL")
        self.save_folder = save_folder
        self.filename = ''

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
            self.data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error al obtener los datos: {e}")
            self.data = False
        pass
        
    def set_current_timestamp(self):
        self.timestamp = datetime.now()
        self.timestamp_str = self.timestamp.strftime("%Y%m%d_%H%M%S")
        pass

    def set_filename(self):
        self.filename = f"{self.save_folder}/{self.timestamp_str}.json"
        pass
    
    def save_data(self):
        self.create_save_folder()  # Crear la carpeta de guardado al inicializar la instancia
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.data, f, indent=4)
            print(f"Datos guardados correctamente en '{self.filename}'")
        except IOError as e:
            print(f"Error al guardar los datos: {e}")
    
    def connect_to_redis(self, host='redis-waze', port=6379, db=0):
        try:
            self.redis_client = redis.StrictRedis(host=host, port=port, db=db)
            print("Conexión a Redis establecida.")
        except redis.ConnectionError as e:
            print(f"No se pudo conectar a Redis: {e}")

    def save_data_to_redis(self):
        if self.redis_client:
            try:
                self.redis_client.set(self.timestamp_str, json.dumps(self.data))
                print(f"Datos guardados en Redis con clave '{self.timestamp_str}'")
            except redis.RedisError as e:
                print(f"Error al guardar los datos en Redis: {e}")
    
    def disconnect_from_redis(self):
        if self.redis_client:
            self.redis_client.close()
            print("Conexión a Redis cerrada.")

class DataTransformer:
    def __init__(self):
        pass

    def set_data(self, data):
        self.data = data
        self.gdfs = {}
        pass

    def set_timestamp(self, timestamp):
        self.timestamp = timestamp
        pass

    def transform_alerts(self):
        from shapely.geometry import Point

        alerts = self.data['alerts']
        alerts_gdf = gpd.GeoDataFrame(alerts)

        def convert_location_to_point(alerts_gdf):
            alerts_gdf['geometry'] = alerts_gdf['location'].apply(lambda loc: Point(loc['x'], loc['y']))
            return alerts_gdf

        def adjust_gdf(alerts_gdf):
            alerts_gdf.drop(columns=['location'], inplace=True)
            alerts_gdf.set_crs(4326, inplace=True)
            alerts_gdf['timestamp'] = self.timestamp
            alerts_gdf['timezone'] = 'UTC'
            return alerts_gdf

        alerts_gdf = convert_location_to_point(alerts_gdf)
        alerts_gdf = adjust_gdf(alerts_gdf)
        self.gdfs['alerts'] = alerts_gdf
        pass

    def transform_jams(self):
        from shapely.geometry import LineString

        jams = self.data['jams']
        jams_gdf = gpd.GeoDataFrame(jams)

        def convert_lines_to_linestrings(jams_gdf):
            jams_gdf['geometry'] = jams_gdf['line'].apply(lambda x: LineString([(point['x'], point['y']) for point in x]))
            return jams_gdf

        def adjust_gdf(jams_gdf):
            jams_gdf.drop(columns=['line', 'segments'], inplace=True)
            jams_gdf.set_crs(4326, inplace=True)
            jams_gdf['timestamp'] = self.timestamp
            jams_gdf['timezone'] = 'UTC'
            return jams_gdf

        jams_gdf = convert_lines_to_linestrings(jams_gdf)
        jams_gdf = adjust_gdf(jams_gdf)
        self.gdfs['jams'] = jams_gdf
        pass

    def transform_json_data(self):
        self.transform_alerts()
        self.transform_jams()
        pass

class DataLoader:
    def __init__(self):
        pass

    def set_data(self, data):
        self.data = data
        pass

    def connect_to_database(self):
        user = 'clbb'
        password = 'pass123'
        host = 'clbb-db'
        port = '5432'
        db = 'geodb'
        self.engine = create_engine(f'postgresql://{user}:{password}@{host}:{port}/{db}')
        pass

    def load_to_database(self):
        for table_name, gdf in self.data.items():
            gdf.to_postgis(f'waze_{table_name}', con=self.engine, if_exists='append', index=False)
        pass

    def disconnect_from_database(self):
        self.engine.dispose()
        pass

def main():
    extractor = DataExtractor()
    transformer = DataTransformer()
    loader = DataLoader()

    extractor.connect_to_redis()

    minutes = os.getenv('minutes', 5)
    minutes = int(minutes)
    print("Captura de Json Waze")

    while True:
        extractor.set_current_timestamp()
        extractor.set_filename()
        extractor.fetch_data()

        if extractor.data:
            extractor.save_data_to_redis()

            transformer.set_data(extractor.data)
            transformer.set_timestamp(extractor.timestamp)
            transformer.transform_json_data()

            loader.set_data(transformer.gdfs)
            loader.connect_to_database()
            loader.load_to_database()
            loader.disconnect_from_database()
        
        print(extractor.timestamp_str)
        time.sleep(minutes*60)

if __name__ == "__main__":
    main()