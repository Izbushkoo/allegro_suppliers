import asyncio
import json
import os.path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database_models import AllegroToken
from app.services.modules.DownloadXML import download_xml, download_with_retry, download_with_retry_sync, \
    download_content_sync
from app.services.modules.DatabaseManager import fetch_data_from_db, update_items_by_sku, update_items_by_allegro_id, \
    fetch_data_from_db_sync, MongoManager
from app.services.modules.ParsingManager import \
    parse_xml_to_json_sync
from app.services.modules.DataFiltering.GetAllData import filter_json_object_to_array_of_objects, \
filter_json_object_to_array_of_objects_with_pydash, filter_json_object_to_array_of_objects_for_adding_to_mongo_map
from app.services.modules.DataFiltering.GetAllegroData import filter_supplier_data_for_allegro, \
    filter_supplier_data_for_category_by_allegro_id
from app.schemas.pydantic_models import CallbackManager
from app.services.modules.APITokenManager import check_token, check_token_sync
from app.services.modules.AlegroApiManager import update_offers, update_offers_sync, update_offers_in_bulks
from app.loggers import ToLog

supplier_name = {
    "pgn": "pgn",
    "unimet": "unimet",
    "hurtprem": "hurtprem",
    "rekman": "rekman",
    "growbox": "growbox"
}


async def get_all_data(supplier, is_offers_should_be_updated_on_allegro, multiplier, callback_manager: CallbackManager):
    # if supplier == "unimet":
    content = await download_with_retry(supplier, callback_manager)
    # else:
    #     await download_xml(supplier)

    database_items = await fetch_data_from_db(supplier, is_offers_should_be_updated_on_allegro)
    json_from_xml = parse_xml_to_json_sync(content)

    ToLog.write_basic("parsed")
    filtered_objects = filter_json_object_to_array_of_objects(
        supplier, json_from_xml, database_items, multiplier
    )
    ToLog.write_basic("filtered")
    return filtered_objects


async def get_all_data_current_test(supplier, multiplier=1.0):
    callback_manager = CallbackManager()

    content = await download_with_retry(supplier, callback_manager)

    database_items = await MongoManager.fetch_positions_for_sale(supplier)

    json_from_xml = parse_xml_to_json_sync(content)

    with open(os.path.join(os.getcwd(), "xml", "curent_js_from_xml.json"), "w") as file:
        file.write(json.dumps(json_from_xml, indent=4))

    filtered_objects = filter_json_object_to_array_of_objects_for_adding_to_mongo_map(
        supplier, json_from_xml, database_items, multiplier
    )
    with open(os.path.join(os.getcwd(), "xml", "curent_filtered.json"), "w") as file:
        file.write(json.dumps(filtered_objects, indent=4))

    total = len(filtered_objects)
    ToLog.write_basic(f"Total: {total}")
    await MongoManager.set_weight_bulks(filtered_objects)
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
    try:
        token = await check_token(database, allegro_token, kwargs.get("callback_manager"))
    except Exception:
        return
    else:
        access_token = token.access_token
        await update_offers(allegro_objects, access_token, **kwargs)


async def fetch_and_update_allegro_bulks(filtered_objects, access_token: str, **kwargs):
    allegro_objects = filter_supplier_data_for_allegro(filtered_objects)
    await update_offers_in_bulks(allegro_objects, access_token, **kwargs)


def fetch_and_update_allegro_sync(database: AsyncSession, filtered_objects, allegro_token: AllegroToken, **kwargs):
    allegro_objects = filter_supplier_data_for_allegro(filtered_objects)
    try:
        token = check_token_sync(database, allegro_token)
    except Exception:
        return
    else:
        access_token = token.access_token
        update_offers_sync(allegro_objects, access_token, **kwargs)


async def turn_off_items_by_category(supplier, category):
    filtered_objects = await get_all_data(supplier, True, 1.0)
    items_to_turn_off = filter_supplier_data_for_category_by_allegro_id(filtered_objects, category)
    ToLog.write_basic(f"Items to turn off: {len(items_to_turn_off)}")
