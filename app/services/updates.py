import json
import os.path

from app.services.modules.DownloadXML import download_with_retry
from app.services.modules.DatabaseManager import MongoManager
from app.services.modules.ParsingManager import parse_xml_to_json_sync
from app.services.modules.DataFiltering.GetAllData import filter_json_object_to_array_of_objects, \
    filter_json_object_to_array_of_objects_for_adding_to_mongo_map, filter_for_supplier_items
from app.services.modules.DataFiltering.GetAllegroData import filter_supplier_data_for_allegro, \
    filter_supplier_data_for_category_by_allegro_id
from app.schemas.pydantic_models import CallbackManager
from app.services.modules.AlegroApiManager import update_offers_in_bulks
from app.loggers import ToLog


async def get_all_data(supplier, multiplier, callback_manager: CallbackManager):
    content = await download_with_retry(supplier, callback_manager)

    database_items = await MongoManager.fetch_positions_for_sale(supplier)
    json_from_xml = parse_xml_to_json_sync(content)

    ToLog.write_basic("parsed")
    filtered_objects = filter_json_object_to_array_of_objects(
        supplier, json_from_xml, database_items, multiplier
    )
    ToLog.write_basic("filtered")
    return filtered_objects


async def get_all_supplier_products_data(supplier, callback_manager: CallbackManager, multiplier):
    content = await download_with_retry(supplier, callback_manager)

    json_from_xml = parse_xml_to_json_sync(content)

    path = os.path.join(os.getcwd(), "xml", "json_for_supplier.json")
    with open(path, "w") as file:
        file.write(json.dumps(json_from_xml, indent=4))

    filtered_objects = filter_for_supplier_items(supplier, json_from_xml, multiplier)

    return filtered_objects


async def get_all_data_current_test(supplier, multiplier=1.0):
    callback_manager = CallbackManager()

    content = await download_with_retry(supplier, callback_manager)

    database_items = await MongoManager.fetch_positions_for_sale(supplier)

    json_from_xml = parse_xml_to_json_sync(content)

    filtered_objects = filter_json_object_to_array_of_objects_for_adding_to_mongo_map(
        supplier, json_from_xml, database_items, multiplier
    )

    total = len(filtered_objects)
    ToLog.write_basic(f"Total: {total}")
    await MongoManager.set_weight_bulks(filtered_objects)
    return filtered_objects


async def fetch_and_update_allegro_bulks(filtered_objects, access_token: str, **kwargs):
    allegro_objects = filter_supplier_data_for_allegro(filtered_objects)
    await update_offers_in_bulks(allegro_objects, access_token, **kwargs)


async def turn_off_items_by_category(supplier, category):
    filtered_objects = await get_all_data(supplier, 1.0)
    items_to_turn_off = filter_supplier_data_for_category_by_allegro_id(filtered_objects, category)
    ToLog.write_basic(f"Items to turn off: {len(items_to_turn_off)}")


async def create_single_offer_on_allegro_with_selection_first():
    """Функция предназначена для создания одного оффера. Ищет совпадение EAN с уже существующим продуктом,
    и если находятся несколько совпадений, пытается создать оффер для самого первого в списке совпадений.
    """

    ...


