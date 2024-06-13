import os
import aiohttp
import asyncio
import csv
from datetime import datetime
from app.services.configs.AmazonConfig import AmazonSettings


async def filter_supplier_data_for_amazon(filtered_objects):
    zl_to_euro_rate = await get_zl_to_euro_rate()

    items_to_delete = []
    items_to_add = []

    for item in filtered_objects:
        if item['stock'] <= 0:
            items_to_delete.append({
                'seller-sku': item['amazon_sku'],
                'add-delete': 'x',
            })
        else:
            price = calculate_amazon_price_in_euro(item['price'], zl_to_euro_rate, AmazonSettings['priceMultiplier']['DE'])
            shipping_template = set_shipping_template_for(price)

            items_to_add.append({
                'sku': item['amazon_sku'],
                'product-id': item['ean'],
                'product-id-type': '4',
                'price': price,
                'item-condition': '11',
                'quantity': item['stock'],
                'add-delete': 'a',
                'handling-time': item['handlingTime'],
                'merchant_shipping_group_name': shipping_template,
                'expedited-shipping': 'N',
            })

    return {'itemsToAdd': items_to_add, 'itemsToDelete': items_to_delete}


def calculate_amazon_price_in_euro(price, currency_rate, multiplier):
    price_in_euro = price * currency_rate
    multiplied_price = price_in_euro * multiplier
    rounded_price = round(multiplied_price + 0.75)
    dot_to_comma_price = str(rounded_price).replace('.', ',')
    return dot_to_comma_price


def set_shipping_template_for(price):
    price_string_to_number = float(price.replace(",", "."))
    if price_string_to_number <= 50:
        return '15_99 flat'
    elif price_string_to_number <= 150:
        return '9_99 flat'
    else:
        return 'Free DE shipping'


async def get_zl_to_euro_rate():
    try:
        api_key = 'qU7kpVMn2IUOhMJwoa3J5516nDh4k9uE'
        url = f"https://api.apilayer.com/exchangerates_data/latest?apikey={api_key}&symbols=PLN,EUR"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception("Failed to fetch exchange rate")
                data = await response.json()
                rates = data['rates']
                eur_rate = rates['EUR'] / rates['PLN']
                return eur_rate
    except Exception as e:
        print('Error fetching exchange rates:', str(e))
        raise e


def generate_tsv(data, headers, filename):
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=headers, delimiter='\t')
        writer.writeheader()
        writer.writerows(data)


def generate_filename(supplier, type_):
    timestamp = datetime.now().isoformat().replace(':', '-').replace('.', '-')
    return f"{supplier}_{type_}_{timestamp}.tsv"


async def fetch_and_write_data_for_amazon(filtered_objects, supplier):
    filtered_data = await filter_supplier_data_for_amazon(filtered_objects)
    items_to_add = filtered_data['itemsToAdd']
    items_to_delete = filtered_data['itemsToDelete']

    amazon_add_items_filename = generate_filename(supplier, AmazonSettings['fileType']['add_items'])
    amazon_remove_items_filename = generate_filename(supplier, AmazonSettings['fileType']['remove_items'])

    generate_tsv(items_to_add, AmazonSettings['tsvHeaders']['add_items'], amazon_add_items_filename)
    generate_tsv(items_to_delete, AmazonSettings['tsvHeaders']['remove_items'], amazon_remove_items_filename)

# Пример использования:
# filtered_objects = ... # Some list of filtered objects
# supplier = 'some_supplier'
# asyncio.run(fetch_and_write_data_for_amazon(filtered_objects, supplier))
