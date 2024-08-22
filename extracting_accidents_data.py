import os
import geopandas as gpd
from sqlalchemy import create_engine
import shutil

# Query data from the database using Geopandas
def query_data_from_postgres(table_name: str, db_connection_string: str) -> None:
    try:
        # Create SQL engine
        engine = create_engine(db_connection_string)

        # Start SQL engine
        with engine.connect() as connection:
            # Connect to the database
            gdf = gpd.read_postgis(
                sql=f"SELECT * FROM {table_name}",
                con=connection,
                geom_col="geometry",
                crs="EPSG:4326"
            )
            return gdf       
        
    except Exception as e:
        print(f"Error querying data from PostgreSQL: {str(e)}")

def export_data(table_name: str, data: gpd.GeoDataFrame, main_save_path: str) -> None:
    try:
        # Create the save path for the Shapefile
        save_path = os.path.join(main_save_path, f"{table_name}")

        # Save the data as Shapefile
        data.to_file(save_path, driver='ESRI Shapefile')

        # Compress the folder into a zip file
        shutil.make_archive(save_path, 'zip', main_save_path, table_name)

        print(f"Data exported as Shapefile: {save_path}")
    except Exception as e:
        print(f"Error exporting data as Shapefile: {str(e)}")

def preprocess_data(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:

    original_timezone = 'UTC'
    new_timezone = 'America/Santiago'
    # Convert timestamp to America/Santiago timezone
    gdf['timestamp'] = gdf['timestamp'].dt.tz_localize(original_timezone).dt.tz_convert(new_timezone)
    gdf['timezone'] = new_timezone
    
    # Extract year, month, and day from the timestamp
    gdf['year'] = gdf['timestamp'].dt.year
    gdf['month'] = gdf['timestamp'].dt.month
    gdf['day'] = gdf['timestamp'].dt.day
    gdf['hour'] = gdf['timestamp'].dt.hour

    # Convert timestamp column to string with format YYYY/MM/DD_HH:MM:SS
    gdf['timestamp'] = gdf['timestamp'].dt.strftime('%Y/%m/%d_%H:%M:%S')

    # Filter unique uuid and keep first record
    gdf = gdf.drop_duplicates(subset='uuid', keep='first')

    # Filter columns
    gdf = gdf[gdf['type'] == 'ACCIDENT']

    return gdf


def main():
    # Get database connection parameters from environment variables
    db_host = 'localhost'
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    # Create database connection string
    db_connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    print(db_connection_string)
    # Check if the 'export' folder exists, if not create it
    if not os.path.exists('export'):
        os.makedirs('export')
    
    # tables = ['waze_alerts', 'waze_jams']
    tables = ['waze_alerts']

    main_save_path = 'export'

    for table_name in tables:
        print(f"Processing table: {table_name}")
        # Query data from the database
        data = query_data_from_postgres(table_name, db_connection_string)
        data = preprocess_data(data)
        export_data(table_name, data, main_save_path)
        pass
    pass

if __name__ == "__main__":
    main()
