import asyncio
import re
import math
import os
import json

import pydash
from jsonpath_ng.ext import parse
from app.services.configs.AllegroConfig import supplier_settings
from app.loggers import ToLog


# Helper functions
def extract_price(price_string, vat, is_vat_included):
    if "," in price_string:
        price_string = price_string.replace(',', '.')
    price_string = re.sub(r'[A-Za-z\s]', '', price_string)
    price = float(price_string)

    if math.isnan(price):
        raise ValueError(f"Invalid price: '{price_string}'")
    if not is_vat_included:
        price *= 1 + (vat / 100)
    return math.ceil(price) - 0.05


def extract_vat(vat_string, is_vat_included):
    if is_vat_included:
        return 0

    vat_str = re.sub(r'[,.\s0%]', '', vat_string)
    if vat_str == "":
        return 0

    vat = float(vat_str)

    if math.isnan(vat):
        raise ValueError(f"Invalid VAT: '{vat_string}'")
    elif vat not in [0, 5, 8, 23]:
        raise ValueError(f"Invalid VAT value: '{vat}'")

    return vat


def calculate_price(price, price_ranges, is_apply_custom_multipliers, is_apply_custom_multiplier, supplier, item_sku,
                    multiplier):
    range_ = next((r for r in price_ranges if price <= r['maxPrice']), None)
    if not range_:
        raise ValueError(f"Price {price} is out of range")

    if range_['factor'] == 'add':
        final_price = price + range_['value']
    elif range_['factor'] == 'multiply':
        final_price = price * range_['value']
    else:
        raise ValueError(f"Invalid price factor: '{range_['factor']}'")

    if is_apply_custom_multipliers:
        custom_multipliers = supplier_settings[supplier]['customMultipliers']
        if item_sku in custom_multipliers:
            final_price *= custom_multipliers[item_sku]

    if is_apply_custom_multiplier:
        custom_multiplier = supplier_settings[supplier].get('customMultiplier')
        if custom_multiplier:
            final_price *= custom_multiplier

    final_price *= multiplier

    return math.ceil(final_price) - 0.05


# def extract_and_calculate_stock(xml_stock):
#     stock = int(xml_stock) if xml_stock.isdigit() else 0
#     return max(min(stock, 100), 0)

def extract_and_calculate_stock(xml_stock):
    # Заменяем запятую на точку
    normalized_stock = xml_stock.replace(',', '.')
    try:
        # Преобразуем в число с плавающей точкой, а затем в целое число
        stock = int(float(normalized_stock))
    except ValueError:
        # Если преобразование не удалось, устанавливаем значение 0
        stock = 0
    # Ограничиваем значение от 0 до 100
    return max(stock, 0)


def extract_and_calculate_weight(xml_weight, supplier):
    # Заменяем запятую на точку
    normalized = xml_weight.replace(',', '.')
    try:
        weight = float(normalized)
    except ValueError:
        weight = "N/A"
    else:
        if supplier not in ["rekman"]:
            weight *= 1000
        if weight == 0:
           weight = "N/A"
    return weight


def format_ean(ean):
    desired_length = 13
    return str(ean).zfill(desired_length)


def replace_polish_characters_in_sku(input_):
    polish_to_english = {
        'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
        'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N', 'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z'
    }
    return re.sub(r'[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]', lambda m: polish_to_english[m.group()], input_)


# Function to convert string values from supplierSettings objects to property
def by_string(json_obj, path):
    properties = path.split('.')
    current_obj = json_obj
    for i, prop in enumerate(properties):
        prev_prop = properties[i - 1] if i > 0 else None
        if prop == 'ean' and prev_prop == 'attrs':
            attrs_array = current_obj.get('a', [])
            ean_obj = next((obj for obj in attrs_array if obj['@name'] == 'EAN'), None)
            current_obj = ean_obj['#text'] if ean_obj else None
            break
        elif '[' in prop and ']' in prop:
            match = re.match(r'(\w+)\[(\d+)\]', prop)
            if match:
                array_prop, index = match.groups()
                current_obj = current_obj[array_prop][int(index)]
        else:
            current_obj = current_obj.get(prop)

    return current_obj


# Final function
def filter_json_object_to_array_of_objects(supplier, json_file, database_items, multiplier=1):
    settings = supplier_settings[supplier]

    products_path = settings['xmlPath']['products']
    sku_path = settings['xmlPath']['sku']
    category_path = settings['xmlPath']['category']
    price_path = settings['xmlPath']['price']
    is_apply_custom_multipliers = settings['applyCustomMultipliers']
    is_apply_custom_multiplier = settings['applyMultiplier']
    vat_path = settings['xmlPath']['vat']
    stock_path = settings['xmlPath']['stock']
    ean_path = settings['xmlPath']['ean']
    price_ranges = settings['priceRanges']
    is_vat_included = settings['isVatIncluded']

    sku_prefix = settings['skuPrefix']
    handling_time = settings['handlingTime']

    all_products = by_string(json_file, products_path)

    product_map = {by_string(product, sku_path): product for product in all_products}

    filtered_objects = []
    for item in database_items:
        sku = item['supplier_sku']
        product = product_map.get(sku)

        if not product:
            filtered_objects.append({
                'allegro_offerta_id': item['allegro_oferta_id'],
                'amazon_sku': f"{sku_prefix}{sku}",
                'stock': 0,
                'price': 7.77,
                'ean': 404,
                'handling_time': handling_time,
                'category': 'N/A'
            })
            continue

        price_string = str(by_string(product, price_path))
        vat_string = str(by_string(product, vat_path))
        stock_string = str(by_string(product, stock_path))
        ean_string = str(by_string(product, ean_path))

        formatted_ean = format_ean(ean_string)
        vat = extract_vat(vat_string, is_vat_included)
        price = extract_price(price_string, vat, is_vat_included)
        final_price = calculate_price(price, price_ranges, is_apply_custom_multipliers, is_apply_custom_multiplier,
                                      supplier, sku, multiplier)
        final_stock = extract_and_calculate_stock(stock_string)
        final_sku = replace_polish_characters_in_sku(f"{sku_prefix}{sku}")
        category = str(by_string(product, category_path))

        filtered_objects.append({
            'allegro_offerta_id': item['allegro_oferta_id'],
            'amazon_sku': final_sku,
            'stock': final_stock,
            'price': final_price,
            'ean': formatted_ean,
            'handlingTime': handling_time,
            'category': category
        })

    return filtered_objects


def filter_json_object_to_array_of_objects_for_adding_to_mongo_map(supplier, json_file, database_items, multiplier=1):
    settings = supplier_settings[supplier]

    products_path = settings['xmlPath']['products']
    weight_path = settings['xmlPath']['weight']
    sku_path = settings['xmlPath']['sku']

    all_products = by_string(json_file, products_path)

    product_map = {by_string(product, sku_path): product for product in all_products}

    filtered_objects = {}
    for item in database_items:
        sku = item['supplier_sku']
        product = product_map.get(sku)

        if not product:
            # filtered_objects.append({
            #     'allegro_offerta_id': item['allegro_oferta_id'],
            #     'weight': "N/A"
            # })
            continue

        weight_string = str(by_string(product, weight_path))

        weight_value = extract_and_calculate_weight(weight_string, supplier)

        filtered_objects[item['allegro_oferta_id']] = weight_value

    return filtered_objects


def jsonpath_search(json_data, path):
    jsonpath_expr = parse(path)
    matches = jsonpath_expr.find(json_data)
    return [match.value for match in matches]


def filter_json_object_to_array_of_objects_with_pydash(supplier, json_file, database_items, multiplier=1):
    settings = supplier_settings[supplier]

    products_path = settings['xmlPath']['products']
    sku_path = settings['xmlPath']['sku']
    category_path = settings['xmlPath']['category']
    price_path = settings['xmlPath']['price']
    is_apply_custom_multipliers = settings['applyCustomMultipliers']
    is_apply_custom_multiplier = settings['applyMultiplier']
    vat_path = settings['xmlPath']['vat']
    stock_path = settings['xmlPath']['stock']
    ean_path = settings['xmlPath']['ean']
    price_ranges = settings['priceRanges']
    is_vat_included = settings['isVatIncluded']

    sku_prefix = settings['skuPrefix']
    handling_time = settings['handlingTime']

    all_products = pydash.get(json_file, products_path, [])

    product_map = {pydash.get(product, sku_path): product for product in all_products}

    filtered_objects = []
    for item in database_items:
        sku = item['supplier_sku']
        product = product_map.get(sku)

        if not product:
            filtered_objects.append({
                'allegro_offerta_id': item['allegro_oferta_id'],
                'amazon_sku': f"{sku_prefix}{sku}",
                'stock': 0,
                'price': 7.77,
                'ean': 404,
                'handling_time': handling_time,
                'category': 'N/A'
            })
            continue

        price_string = str(pydash.get(product, price_path, ""))
        vat_string = str(pydash.get(product, vat_path, ""))
        stock_string = str(pydash.get(product, stock_path, ""))
        ean_string = str(jsonpath_search(product, ean_path)[0])

        formatted_ean = format_ean(ean_string)
        vat = extract_vat(vat_string, is_vat_included)
        price = extract_price(price_string, vat, is_vat_included)
        final_price = calculate_price(price, price_ranges, is_apply_custom_multipliers, is_apply_custom_multiplier,
                                      supplier, sku, multiplier)
        final_stock = extract_and_calculate_stock(stock_string)
        final_sku = replace_polish_characters_in_sku(f"{sku_prefix}{sku}")
        category = str(pydash.get(product, category_path, "N/A"))

        filtered_objects.append({
            'allegro_offerta_id': item['allegro_oferta_id'],
            'amazon_sku': final_sku,
            'stock': final_stock,
            'price': final_price,
            'ean': formatted_ean,
            'handlingTime': handling_time,
            'category': category
        })

    return filtered_objects
