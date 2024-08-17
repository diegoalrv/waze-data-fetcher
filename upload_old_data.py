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

from glob import glob

# Ignorar todas las advertencias
warnings.filterwarnings("ignore")

class DataReader:
    def __init__(self):
        self.timestamp = None
        self.data = None

    def read_file(self, filename):
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File '{filename}' not found in folder '{self.folder_path}'")

        timestamp_str = os.path.split(filename)[-1]  # Remove file extension
        self.timestamp_str = timestamp_str.replace('.json', '')
        try:
            self.timestamp = pd.to_datetime(self.timestamp_str, format='%Y%m%d_%H%M%S')
        except ValueError:
            raise ValueError("Invalid timestamp format in filename")

        # Read JSON data from file
        with open(filename, 'r') as file:
            self.data = json.load(file)

    def connect_to_redis(self, host='localhost', port=6379, db=0):
        try:
            self.redis_client = redis.StrictRedis(host=host, port=port, db=db)
            print("Conexión a Redis establecida.")
        except redis.ConnectionError as e:
            print(f"No se pudo conectar a Redis: {e}")

    def get_data_uploaded(self):
        keys = self.redis_client.keys("*")
        keys = [byte.decode('utf-8') for byte in keys]
        return keys

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
        host = 'localhost'
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
    reader = DataReader()
    transformer = DataTransformer()
    loader = DataLoader()

    reader.connect_to_redis()
    json_files = glob('./data/*.json')
    uploaded_files = reader.get_data_uploaded()

    # Filtrar archivos que no están en la lista de archivos subidos
    remaining_data = [archivo for archivo in json_files if archivo not in uploaded_files]

    total = len(json_files)

    for i, file in enumerate(remaining_data):
        print(file)
        print(f'{i}/{total}')
        print('reading_files')
        reader.read_file(file)
        print('guardando en redis')
        reader.save_data_to_redis()
        try:
            transformer.set_data(reader.data)
            transformer.set_timestamp(reader.timestamp)
            transformer.transform_json_data()

            loader.set_data(transformer.gdfs)
            loader.connect_to_database()
            loader.load_to_database()
            loader.disconnect_from_database()
        except Exception as e:
            print("Se ha producido un error:", e)
            
if __name__ == "__main__":
    main()