from typing import List

import httpx
import asyncio

from app.loggers import ToLog
from app.services.modules.AlegroApiManager import create_single_offer, update_offers_status
from app.services.modules.DatabaseManager import MongoManager
from app.schemas.pydantic_models import CallbackManager, SynchronizeOffersRequest
from app.services.modules.AlegroApiManager import search_product_by_ean_return_first, search_product_by_ean, \
    get_product_details, update_status_single_offer
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

    ToLog.write_basic(f"length of failed eans: {len(failed_eans)}")
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
            ToLog.write_basic(f"Written to FailedEans {len(all_failed_eans)}")
    ToLog.write_basic(f"Synchronization Finished")


async def make_single_oferta_check(product_from_mongo, access_token):

    ean = product_from_mongo["ean"]
    allegro_product_id = product_from_mongo["allegro_product_id"]
    ToLog.write_basic(f"product id {allegro_product_id}")
    offer_id = product_from_mongo["allegro_oferta_id"]
    products = await search_product_by_ean(ean, access_token)
    allegro_product_details = await get_product_details(allegro_product_id, access_token)
    ToLog.write_basic(f"{allegro_product_details}")
    allegro_eans = None
    for param in allegro_product_details["parameters"]:
        if param["id"] == "225693" or param["name"] == "EAN (GTIN)":
            allegro_eans = param

    if allegro_eans:
        if len(allegro_eans["values"]) != 1:
            return {"id": offer_id}

    if len(products) != 1:
        return {"id": offer_id}


async def disable_multiple_ean_offers(access_token, products, callback_manager, batch: int = 50):

    for i in range(0, len(products), batch):
        tasks = []
        for product in products[i: i + batch]:
            task = asyncio.create_task(make_single_oferta_check(product, access_token))
            tasks.append(task)
            results = await asyncio.gather(*tasks)
            array_to_deactivate = [result for result in results if result]
            await MongoManager.set_we_sell_to([offer["id"] for offer in array_to_deactivate], False)
            try:
                await update_offers_status(access_token, array_to_deactivate, "END", callback_manager)
                ToLog.write_basic(f"Deactivated {len(array_to_deactivate)} offertas")
            except Exception:
                await MongoManager.set_we_sell_to([offer["id"] for offer in array_to_deactivate], True)

    ToLog.write_basic(f"Deactivation finished")
