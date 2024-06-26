import json
import os.path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database_models import AllegroToken
from app.services.modules.DownloadXML import download_xml, download_with_retry, download_with_retry_sync, \
    download_content_sync
from app.services.modules.DatabaseManager import fetch_data_from_db, update_items_by_sku, update_items_by_allegro_id, \
    fetch_data_from_db_sync
from app.services.modules.ParsingManager import parse_xml_to_json, parse_xml_to_json_test, \
    parse_xml_to_json_sync
from app.services.modules.DataFiltering.GetAllData import filter_json_object_to_array_of_objects, filter_json_object_to_array_of_objects_with_pydash
from app.services.modules.DataFiltering.GetAllegroData import filter_supplier_data_for_allegro, filter_supplier_data_for_category, \
    filter_supplier_data_for_category_by_allegro_id
from app.services.modules.APITokenManager import check_token, check_token_sync
from app.services.modules.AlegroApiManager import update_offers, update_offers_sync
from app.loggers import ToLog

supplier_name = {
    "pgn": "pgn",
    "unimet": "unimet",
    "hurtprem": "hurtprem",
    "rekman": "rekman",
    "growbox": "growbox"
}


async def get_all_data_test(supplier, is_offers_should_be_updated_on_allegro, multiplier):
    await download_xml(supplier)

    database_items = await fetch_data_from_db(supplier, is_offers_should_be_updated_on_allegro)
    if supplier == "unimet":
        json_from_xml = parse_xml_to_json(supplier)
    else:
        json_from_xml = parse_xml_to_json_test(supplier)

    filtered_objects = filter_json_object_to_array_of_objects_with_pydash(supplier, json_from_xml, database_items,
                                                                          multiplier)
    return filtered_objects


async def get_all_data(supplier, is_offers_should_be_updated_on_allegro, multiplier):
    if supplier == "unimet":
        await download_with_retry(supplier)
    else:
        await download_xml(supplier)

    database_items = await fetch_data_from_db(supplier, is_offers_should_be_updated_on_allegro)
    json_from_xml = parse_xml_to_json(supplier)
    with open(os.path.join(os.getcwd(), "xml", f"{supplier}.json"), "w") as file:
        file.write(json.dumps(json_from_xml, indent=4))
    ToLog.write_basic("parsed")
    filtered_objects = filter_json_object_to_array_of_objects(
        supplier, json_from_xml, database_items, multiplier
    )
    ToLog.write_basic("filtered")
    return filtered_objects


def get_all_data_sync(supplier, is_offers_should_be_updated_on_allegro, multiplier):
    xml_content = download_with_retry_sync(supplier)

    database_items = fetch_data_from_db_sync(supplier, is_offers_should_be_updated_on_allegro)

    json_from_xml = parse_xml_to_json_sync(xml_content)
    ToLog.write_basic("parsed")

    filtered_objects = filter_json_object_to_array_of_objects(
        supplier, json_from_xml, database_items, multiplier
    )
    ToLog.write_basic("filtered")
    return filtered_objects


async def fetch_and_update_allegro(database: AsyncSession, filtered_objects, allegro_token: AllegroToken, **kwargs):
    allegro_objects = filter_supplier_data_for_allegro(filtered_objects)
    token = await check_token(database, allegro_token)
    access_token = token.access_token
    await update_offers(allegro_objects, access_token, **kwargs)


def fetch_and_update_allegro_sync(database: AsyncSession, filtered_objects, allegro_token: AllegroToken, **kwargs):
    allegro_objects = filter_supplier_data_for_allegro(filtered_objects)
    token = check_token_sync(database, allegro_token)
    access_token = token.access_token
    update_offers_sync(allegro_objects, access_token, **kwargs)


async def turn_off_items_by_category(supplier, category):
    filtered_objects = await get_all_data(supplier, True, 1.0)
    items_to_turn_off = filter_supplier_data_for_category_by_allegro_id(filtered_objects, category)
    ToLog.write_basic(f"Items to turn off: {len(items_to_turn_off)}")
    await update_items_by_allegro_id(supplier, items_to_turn_off)

