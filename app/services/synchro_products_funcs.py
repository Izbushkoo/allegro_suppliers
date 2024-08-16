from typing import List

import httpx
import asyncio

from app.loggers import ToLog
from app.services.modules.AlegroApiManager import create_single_offer
from app.services.modules.DatabaseManager import MongoManager
from app.schemas.pydantic_models import CallbackManager, SynchronizeOffersRequest
from app.services.modules.AlegroApiManager import search_product_by_ean_return_first
from app.api import deps
from app.services.failed_eans import get_all_failed_eans, add_failed_ean


async def handle_single_product(supplier_product, allegro_access_token):

    ean = supplier_product["ean"]
    try:
        if ean:
            if supplier_product["stock"] > 1:
                if supplier_product["price"] <= 5000:

                    try:
                        found_product = await search_product_by_ean_return_first(ean, allegro_access_token)
                    except httpx.TimeoutException as err:
                        return None, ean
                    if found_product:
                        ToLog.write_basic(f"Start process found product with ean: {ean}")
                        product_to_work_with = {
                            **supplier_product,
                            "allegro_product_id": found_product["id"],
                            "category_id": found_product["category"]["id"],
                            "product_name": found_product["name"]
                        }
                        allegro_response = await create_single_offer(product_to_work_with,
                                                                     access_token=allegro_access_token)
                        if allegro_response:
                            product_to_work_with["allegro_oferta_id"] = allegro_response["id"]
                            product_to_work_with["allegro_we_sell_it"] = True
                            product_to_work_with.pop("price")
                            product_to_work_with.pop("stock")

                            ToLog.write_basic(f"Created offer with id {product_to_work_with['allegro_oferta_id']}")
                            return product_to_work_with, None
        return None, ean
    except Exception as er:
        ToLog.write_error(f"Error {er} \n skiped product with ean {ean}")
        return None, ean


async def process_complete_synchro_task(synchro_config: SynchronizeOffersRequest, access_token, products,
                                        existing_ofertas: List, batch: int = 50):

    database = deps.AsyncSessLocal()

    with_failed_include = synchro_config.with_failed_ean_include
    failed_eans = await get_all_failed_eans(database)

    for i in range(0, len(products), batch):

        tasks = []
        for product in products[i: i + batch]:
            if product["supplier_sku"] not in existing_ofertas:
                if not with_failed_include and product['ean'] in failed_eans:
                    continue

                task = asyncio.create_task(handle_single_product(product, access_token))
                tasks.append(task)
        results = await asyncio.gather(*tasks)
        all_results = [result for result in results]
        all_records = [rec[0] for rec in all_results if rec[0]]
        all_failed_eans = [rec[1] for rec in all_results if rec[1]]

        if all_records:
            await MongoManager.append_bulks_with_retry(all_records, synchro_config.supplier)
            ToLog.write_basic(f"Added to Mongo {len(all_records)} documents")
        if all_failed_eans:
            await add_failed_ean(database, all_failed_eans)
    ToLog.write_basic(f"Synchronization Finished")

