def filter_supplier_data_for_allegro(filtered_objects):
    allegro_objects = [
        {
            "id": item['allegro_offerta_id'],
            "stock": item['stock'],
            "price": item['price']
        }
        for item in filtered_objects
    ]
    return allegro_objects


def filter_supplier_data_for_category(filtered_objects, category):
    allegro_objects = [
        {
            "id": item['allegro_offerta_id'],
            "stock": 0,
            "price": 77.77
        }
        for item in filtered_objects if category in item['category']
    ]
    return allegro_objects


def filter_supplier_data_for_category_by_allegro_id(filtered_objects, category):
    items_to_turn_off = [
        item['allegro_offerta_id']
        for item in filtered_objects if category in item['category']
    ]
    return items_to_turn_off

# Example usage:
# filtered_objects = ... # Some list of filtered objects
# allegro_objects = filter_supplier_data_for_allegro(filtered_objects)
# print(allegro_objects)
# category_objects = filter_supplier_data_for_category(filtered_objects, 'some_category')
# print(category_objects)
# category_by_id = filter_supplier_data_for_category_by_allegro_id(filtered_objects, 'some_category')
# print(category_by_id)
