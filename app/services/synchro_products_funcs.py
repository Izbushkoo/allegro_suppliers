import json
import os
import re
from textwrap import indent
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
    offer_id = product_from_mongo["allegro_oferta_id"]

    try:
        products = await search_product_by_ean(ean, access_token)
        allegro_product_details = await get_product_details(allegro_product_id, access_token)

        if not products or len(products) != 1:
            ToLog.write_basic(f"Offer id to deactivate {offer_id}")
            return {"id": offer_id}

        allegro_eans = None
        if allegro_product_details:
            for param in allegro_product_details["parameters"]:
                if param["id"] == "225693" or param["name"] == "EAN (GTIN)":
                    allegro_eans = param
        else:
            ToLog.write_basic(f"Can't get product details for {offer_id}")
            return {"id": offer_id}

        if allegro_eans:
            if len(allegro_eans["values"]) != 1:
                ToLog.write_basic(f"Offer id to deactivate {offer_id}")
                return {"id": offer_id}

    except Exception:
        return {"id": offer_id}


async def check_offer_product_for_word_containing(word: str, product_from_mongo, access_token):

    try:
        allegro_product_id = product_from_mongo["allegro_product_id"]
        offer_id = product_from_mongo["allegro_oferta_id"]
        allegro_product_details = await get_product_details(allegro_product_id, access_token)

        if allegro_product_details:
            description = allegro_product_details["description"]
            found_descriptions = []
            for section in description["sections"]:
                for item in section["items"]:
                    if item["type"] == "TEXT":
                        content = item["content"]
                        pattern = re.compile(re.escape(word), re.IGNORECASE)
                        if pattern.search(content):
                            found_descriptions.append(section)
            if found_descriptions:
                to_return = {
                    offer_id: found_descriptions
                }
                ToLog.write_basic(f"Found {to_return}")
                return to_return
    except Exception:
        return


async def disable_multiple_ean_offers(access_token, products, callback_manager, batch: int = 50):
    ToLog.write_basic(f"Total ofers to process {len(products)}")
    count = 0
    file_path_not_processed = os.path.join(os.getcwd(), "logs", "not_processed.json")
    file_path_processed = os.path.join(os.getcwd(), "logs", "processed.json")

    try:
        with open(file_path_not_processed, "r") as file:
            written_not_processed = json.loads(file.read())
    except (FileExistsError, FileNotFoundError):
        written_not_processed = []

    try:
        with open(file_path_processed, "r") as file:
            written_processed = json.loads(file.read())
    except (FileExistsError, FileNotFoundError):
        written_processed = []

    for i in range(0, len(products), batch):
        tasks = []
        for product in products[i: i + batch]:
            if product["allegro_oferta_id"] in written_processed:
                continue
            task = asyncio.create_task(make_single_oferta_check(product, access_token))
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        array_to_deactivate = [result for result in results if result]
        offers_to_deactivate = [offer["id"] for offer in array_to_deactivate]
        try:
            await update_mongo_with_retry(offers_to_deactivate, False)
        except RuntimeError:
            written_not_processed += offers_to_deactivate

        try:
            await update_offers_status(access_token, array_to_deactivate, "END", callback_manager)
            ToLog.write_basic(f"Deactivated {len(array_to_deactivate)} offertas")
        except Exception as err:
            ToLog.write_basic(f"Error during update offers status {err}")
            written_not_processed += offers_to_deactivate
            continue
        else:
            written_processed += offers_to_deactivate

        with open(file_path_processed, "w") as file:
            file.write(json.dumps(written_processed, indent=4))
        with open(file_path_not_processed, "w") as file:
            file.write(json.dumps(written_not_processed, indent=4))

        count += batch
        ToLog.write_basic(f"Processed {count} offers")
    ToLog.write_basic(f"Deactivation finished")


async def update_mongo_with_retry(offer_ids, flag, retries: int = 10):
    current_retry = 0
    while current_retry < retries:
        try:
            await MongoManager.set_we_sell_to(offer_ids, flag)
        except Exception as err:
            ToLog.write_basic(f"Retry: {current_retry + 1}. Some err {err}. Retry in 10 sec...")
            await asyncio.sleep(10)
            current_retry += 1
            continue
        else:
            return
    raise RuntimeError("Mongo update failed 10 times")


async def get_found_word_in_description(word: str, access_token, products, callback_manager, batch: int = 50):
    ToLog.write_basic(f"Total ofers to process {len(products)}")
    count = 0
    offers = {}
    for i in range(0, len(products), batch):
        tasks = []
        for product in products[i: i + batch]:
            task = asyncio.create_task(check_offer_product_for_word_containing(word, product, access_token))
            tasks.append(task)
            await asyncio.sleep(0.3)

        results = await asyncio.gather(*tasks)
        found = [result for result in results if result]
        for item in found:
            offers.update(item)
        count += batch
        ToLog.write_basic(f"Processed {count} offers")
    base_path = os.path.join(os.getcwd(), "logs", "to_check.json")
    with open(base_path, "w", encoding="utf-8") as file:
        file.write(json.dumps(offers, indent=4, ensure_ascii=False))
    ToLog.write_basic(f"Finished. Found {len(offers.keys())}")