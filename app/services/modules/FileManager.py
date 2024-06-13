import os
import json


def write_to_txt_file(supplier, allegro_objects):
    file_path = f'./final/{supplier}.txt'
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(allegro_objects, file, ensure_ascii=False, indent=4)
        print(f'File {file_path} written successfully.')
    except Exception as e:
        print(f'Error writing file {file_path}: {e}')

# Пример использования:
# allegro_objects = [...] # Some list of allegro objects
# supplier = 'some_supplier'
# write_to_txt_file(supplier, allegro_objects)
