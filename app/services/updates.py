from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database_models import AllegroToken
from app.services.modules.DownloadXML import download_xml
from app.services.modules.DatabaseManager import fetch_data_from_db, update_items_by_sku, update_items_by_allegro_id
from app.services.modules.ParsingManager import parse_xml_to_json
from app.services.modules.DataFiltering.GetAllData import filter_json_object_to_array_of_objects
from app.services.modules.DataFiltering.GetAllegroData import filter_supplier_data_for_allegro, filter_supplier_data_for_category, \
    filter_supplier_data_for_category_by_allegro_id
from app.services.modules.DataFiltering.GetAmazonData import fetch_and_write_data_for_amazon
from app.services.modules.APITokenManager import check_token
from app.services.modules.AlegroApiManager import update_offers, send_telegram_message

supplier_name = {
    "pgn": "pgn",
    "unimet": "unimet",
    "hurtprem": "hurtprem",
    "rekman": "rekman",
    "growbox": "growbox"
}


async def get_all_data(supplier, is_offers_should_be_updated_on_allegro, multiplier):
    await download_xml(supplier)

    database_items = await fetch_data_from_db(supplier, is_offers_should_be_updated_on_allegro)
    json_from_xml = parse_xml_to_json(supplier)

    filtered_objects = filter_json_object_to_array_of_objects(supplier, json_from_xml, database_items, multiplier)
    return filtered_objects


async def fetch_and_update_allegro(database: AsyncSession, filtered_objects, allegro_token: AllegroToken, **kwargs):
    allegro_objects = filter_supplier_data_for_allegro(filtered_objects)
    token = await check_token(database, allegro_token)
    access_token = token.access_token
    await update_offers(allegro_objects, access_token, **kwargs)


async def turn_off_items_by_category(supplier, category):
    filtered_objects = await get_all_data(supplier, True, 1.0)
    items_to_turn_off = filter_supplier_data_for_category_by_allegro_id(filtered_objects, category)
    print(len(items_to_turn_off))
    await update_items_by_allegro_id(supplier, items_to_turn_off)

