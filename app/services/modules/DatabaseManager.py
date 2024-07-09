import os
from contextlib import asynccontextmanager
import asyncio
from typing import List, Dict

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

from app.core.config import settings
from app.loggers import ToLog


supplier_database_id = {
    "pgn": "63d41080b4d9fc9a7f1aeb25",
    "unimet": "63d4110fb4d9fc9a7f1aeb28",
    "hurtprem": "63d39858b4d9fc9a7f1acedb",
    "rekman": "6400778b7b4bb4cab20ccccf",
    "growbox": "640f0ddec6defcd7745fe210"
}

base_uri = settings.MONGO_URI
base_db_name = settings.DB_NAME
base_db_collection = settings.DB_COLL


class MongoBaseManager:

    def __init__(self,
                 uri: str | None = None,
                 db_name: str | None = None,
                 db_collection: str | None = None):
        self.uri = uri or base_uri
        self.db_name = db_name or base_db_name
        self.db_collection = db_collection or base_db_collection

    @asynccontextmanager
    def _connect(self) -> AsyncIOMotorClient:
        client = AsyncIOMotorClient(self.uri)
        try:
            yield client
        finally:
            client.close()

    async def fetch_positions_for_sale(self, supplier):

        supplier_id = supplier_database_id[supplier]
        async with self._connect() as db_manager:
            database = db_manager[base_db_name]
            collection = database[base_db_collection]

            query = {
                "groups": supplier_id,
                "allegro_we_sell_it": True
            }

            projection = {"allegro_oferta_id": 1, "supplier_sku": 1, "_id": 0, "weight": 1}
            documents = collection.find(query, projection)

            items_array = await documents.to_list(length=None)
            return items_array

    async def remove_position_by_allegro_id(self, allegro_id: str | int):

        async with self._connect() as db_manager:
            database = db_manager[base_db_name]
            collection = database[base_db_collection]
            return await collection.delete_one({"allegro_oferta_id": str(allegro_id)})

    async def remove_positions_by_allegro_id_bulk(self, allegro_ids: List[str | int]):

        async with self._connect() as db_manager:
            database = db_manager[base_db_name]
            collection = database[base_db_collection]
            query = {
                "allegro_oferta_id": {
                    "$in": allegro_ids
                }
            }
            return await collection.delete_many(query)
    
    


async def fetch_data_from_db(supplier, allegro_update):
    client = AsyncIOMotorClient(base_uri)
    supplier_id = supplier_database_id[supplier]
    try:
        database = client[base_db_name]
        collection = database[base_db_collection]

        query = {
            "groups": supplier_id,
            "allegro_we_sell_it": allegro_update
        }

        projection = {"allegro_oferta_id": 1, "supplier_sku": 1, "_id": 0}
        documents = collection.find(query, projection)

        items_array = await documents.to_list(length=None)
        return items_array
    finally:
        client.close()


def fetch_data_from_db_sync(supplier, allegro_update):
    client = MongoClient(base_uri)
    supplier_id = supplier_database_id[supplier]
    try:
        database = client[base_db_name]
        collection = database[base_db_collection]

        query = {
            "groups": supplier_id,
            "allegro_we_sell_it": allegro_update
        }
        projection = {"allegro_oferta_id": 1, "supplier_sku": 1, "_id": 0}
        documents = collection.find(query, projection)

        items_array = list(documents)
        return items_array
    finally:
        client.close()


def add_fields(fields: Dict):
    MONGO_URI = "mongodb+srv://BAS:BAS2023_@cluster0.tsfucjd.mongodb.net/?retryWrites=true&w=majority"
    DB_NAME = "SuppliersSkuMap"
    DB_COLL = "res_new"

    client = MongoClient(MONGO_URI)
    try:
        database = client[DB_NAME]
        collection = database[DB_COLL]
        result = collection.update_many({}, {"$set": fields})
        print(result)
    finally:
        client.close()


async def update_items_by_sku(supplier, skus):
    client = AsyncIOMotorClient(base_uri)
    if not supplier or not skus or len(skus) == 0:
        print("Supplier or SKUs not provided")
        return

    supplier_id = supplier_database_id[supplier]

    cleaned_skus = [sku.split("_", 2)[-1] for sku in skus]

    try:
        database = client[base_db_name]
        collection = database[base_db_collection]

        filter_ = {
            "groups": supplier_id,
            "supplier_sku": {"$in": cleaned_skus}
        }

        update = {
            "$set": {"allegro_we_update_it": False}
        }

        result = await collection.update_many(filter_, update)
        ToLog.write_basic(f"{result.modified_count} document(s) was/were updated.")
    except Exception as error:
        ToLog.write_error(f"Error updating documents: {error}")
    finally:
        client.close()


async def update_items_by_allegro_id(supplier, allegro_ids):
    if not supplier or not allegro_ids or len(allegro_ids) == 0:
        ToLog.write_basic("Supplier or IDs not provided")
        return

    supplier_id = supplier_database_id[supplier]

    client = AsyncIOMotorClient(uri)
    try:
        database = client[db_name]
        collection = database[db_collection]

        filter_ = {
            "groups": supplier_id,
            "allegro_oferta_id": {"$in": allegro_ids}
        }
        # print(filter_)
        update = {
            "$set": {"allegro_we_update_it": False}
        }
        result = await collection.update_many(filter_, update)
        # print(result)
        ToLog.write_basic(f"{result.modified_count} document(s) was/were updated.")
    except Exception as error:
        ToLog.write_error(f"Error updating documents: {error}")
    finally:
        client.close()

MongoManager = MongoBaseManager()

