from contextlib import asynccontextmanager
import asyncio
from typing import List, Dict, Any

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient, UpdateOne, InsertOne

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
    async def _connect(self) -> AsyncIOMotorClient:
        client = AsyncIOMotorClient(
            self.uri
        )
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

    async def fetch_positions_all(self, supplier):

        supplier_id = supplier_database_id[supplier]
        async with self._connect() as db_manager:
            database = db_manager[base_db_name]
            collection = database[base_db_collection]

            query = {
                "groups": supplier_id,
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

    async def set_we_sell_to(self, allegro_ids: List[str | int], to_set_value: bool = False):

        async with self._connect() as db_manager:
            database = db_manager[base_db_name]
            collection = database[base_db_collection]
            query = {
                "$set": {
                    "allegro_we_sell_it": to_set_value,
                }
            }
            filter_ = {
                "allegro_oferta_id": {
                    "$in": allegro_ids
                }
            }
            return await collection.update_many(filter_, query)

    async def set_weight(self, allegro_id, weight: float | int):
        """Устанавливает значение веса для записи с заданным 'allegro_oferta_id'"""
        async with self._connect() as db_manager:
            database = db_manager[base_db_name]
            collection = database[base_db_collection]
            query = {
                "$set": {
                    "weight": weight
                }
            }
            filter_ = {
                "allegro_oferta_id": allegro_id
            }
            for attempt in range(5):
                try:
                    return await collection.update_one(filter_, query)
                except Exception as err:
                    ToLog.write_basic(f"{err}")
                    if attempt == 4:
                        raise
                    await asyncio.sleep(2 ** attempt)

    async def set_weight_bulks(self, weights: Dict):
        """Аргумент 'weights - словарь, где ключ - allegro_oferta_id, значение - weight"""
        async with self._connect() as db_manager:
            database = db_manager[base_db_name]
            collection = database[base_db_collection]

            bulk_updates = []
            for item in weights.items():
                bulk_updates.append(
                    UpdateOne(
                        {"allegro_oferta_id": item[0]},
                        {"$set": {
                            "weight": item[1]
                        }}
                    )
                )

            for attempt in range(5):
                try:
                    if bulk_updates:
                        return await collection.bulk_write(bulk_updates, ordered=False)
                    else:
                        ToLog.write_basic("No documents to update.")
                except Exception as err:
                    ToLog.write_basic(f"{err}")
                    if attempt == 4:
                        raise
                    await asyncio.sleep(2 ** attempt)

    async def append_bulks(self, documents: List, supplier: str):
        """

        """
        async with self._connect() as db_manager:
            database = db_manager[base_db_name]
            collection = database[base_db_collection]

            append_bulks = []
            for item in documents:
                append_bulks.append(
                    InsertOne({**item, "groups": supplier_database_id[supplier]})
                )

            for attempt in range(5):
                try:
                    if append_bulks:
                        return await collection.bulk_write(append_bulks, ordered=False)
                    else:
                        ToLog.write_basic("No documents to insert.")
                except Exception as err:
                    ToLog.write_basic(f"{err}")
                    if attempt == 4:
                        raise
                    await asyncio.sleep(2 ** attempt)


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


MongoManager = MongoBaseManager()

