from typing import List

import httpx
import asyncio

from app.loggers import ToLog
from app.services.modules.AlegroApiManager import create_single_offer
from app.services.modules.DatabaseManager import MongoManager
from app.schemas.pydantic_models import CallbackManager, SynchronizeOffersRequest
from app.services.modules.AlegroApiManager import search_product_by_ean_return_first


async def handle_single_product(supplier_product, allegro_access_token):

    ean = supplier_product["ean"]
    if ean:
        try:
            found_product = await search_product_by_ean_return_first(ean, allegro_access_token)
        except httpx.TimeoutException as err:
            return None
        if found_product:
            if supplier_product["stock"] > 0:
                product_to_work_with = {
                    **supplier_product,
                    "allegro_product_id": found_product["id"],
                    "category_id": found_product["category"]["id"],
                    "product_name": found_product["name"]
                }
                allegro_response = await create_single_offer(product_to_work_with, access_token=allegro_access_token)
                if allegro_response:
                    product_to_work_with["allegro_oferta_id"] = allegro_response["id"]
                    product_to_work_with["allegro_we_sell_it"] = True
                    product_to_work_with.pop("price")
                    product_to_work_with.pop("stock")

                    ToLog.write_basic(f"Created offer with id {product_to_work_with['allegro_oferta_id']}")
                    return product_to_work_with


async def process_complete_synchro_task(synchro_config: SynchronizeOffersRequest, access_token, products,
                                        existing_ofertas: List, batch: int = 50):

    for i in range(0, len(products), batch):
        tasks = []
        for product in products[i: i + batch]:
            if product["supplier_sku"] not in existing_ofertas:
                task = asyncio.create_task(handle_single_product(product, access_token))
                tasks.append(task)
        results = await asyncio.gather(*tasks)
        all_results = [result for result in results if result]
        ToLog.write_basic(f"Added to Mongo {len(all_results)} documents")
        await MongoManager.append_bulks(all_results, synchro_config.supplier)

    ToLog.write_basic(f"Synchronization Finished")
