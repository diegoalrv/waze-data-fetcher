import json
import pandas as pd

# Nombre del archivo JSON
json_file = 'data_types_feed.json'

# Función para leer el JSON y transformarlo en un DataFrame
def json_to_dataframe(json_file):
    # Leer el archivo JSON
    with open(json_file, 'r') as f:
        data = json.load(f)

    # Inicializar lista para los datos
    rows = []

    # Extraer cada conjunto de datos (alerts, traffic, irregularities) y sus elementos
    for category, elements in data.items():
        for key, value in elements.items():
            row = {
                'category': category,
                'element': key,
                'type': value['type'],
                'description': value['description']
            }
            rows.append(row)

    # Convertir la lista a DataFrame
    df = pd.DataFrame(rows)

    # Mapeo de tipos de datos compatibles en Python
    type_mapping = {
        'Timestamp': 'datetime64[ns]',
        'Coordinates': 'object',
        'String': 'str',
        'Integer': 'int64',
        'Float': 'float64',
        'Boolean': 'bool',
        'List': 'object',
        'Long Integer': 'int64',
        'Unix Date in Milliseconds': 'int64',
        'Date Timestamp': 'datetime64[ns]',
        'Number': 'float64'
    }

    # Cambiar los valores de la columna 'type' para que sean compatibles con pandas
    df['type'] = df['type'].map(type_mapping)

    return df

# Función para convertir el DataFrame en un diccionario con los tipos de datos
def dataframe_to_data_types_dict(df):
    # Crear un diccionario vacío
    data_types_dict = {}

    # Agrupar por la categoría (alerts, traffic, irregularities)
    grouped = df.groupby('category')

    # Recorrer cada categoría y crear el diccionario de tipos
    for category, group in grouped:
        category_dict = {}
        for _, row in group.iterrows():
            category_dict[row['element']] = row['type']
        data_types_dict[category] = category_dict

    return data_types_dict

# Ejecutar la función y obtener el DataFrame
df_waze = json_to_dataframe(json_file)

# Convertir el DataFrame en un diccionario con los tipos de datos
data_types_dict = dataframe_to_data_types_dict(df_waze)

# Mostrar el diccionario
print(json.dumps(data_types_dict, indent=4))

# Guardar el DataFrame en un archivo CSV para uso posterior
df_waze.to_csv('waze_data_types.csv', index=False)

import json

# Función para guardar el diccionario como un archivo JSON
def save_data_types_dict_to_json(data_types_dict, file_name='waze_data_types.json'):
    # Abrir el archivo en modo de escritura
    with open(file_name, 'w') as f:
        # Guardar el diccionario en formato JSON con indentación para que sea legible
        json.dump(data_types_dict, f, indent=4)

    print(f"El archivo {file_name} ha sido guardado exitosamente.")

# Uso de la función
save_data_types_dict_to_json(data_types_dict)
