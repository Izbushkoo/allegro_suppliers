import json
import time
import uuid
import math
import asyncio
import re
import os
from typing import List

import httpx
import requests

from app.loggers import ToLog
from app.utils import EscapedManager
from app.schemas.pydantic_models import CallbackManager, OffersRequest, UpdateOffersRequest
from app.services.modules.DatabaseManager import MongoManager


limits = httpx.Limits(max_connections=500, max_keepalive_connections=100)
timeout = httpx.Timeout(20.0, connect=5.0)


async def get_page_offers(offers_request, access_token):

    url = f"https://api.allegro.pl/sale/offers"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/vnd.allegro.public.v1+json",
        "Accept": "application/vnd.allegro.public.v1+json",
    }
    params = {
        **offers_request.model_dump(by_alias=True),
        # "limit": limit,
        # "offset": offset
    }

    ToLog.write_basic(f"Params {params}")
    async with (httpx.AsyncClient(limits=limits, timeout=timeout) as client):
        result = await client.get(url, params=params, headers=headers)
        result.raise_for_status()
        result_json = result.json()

        required_data = list(map(lambda x: {
            "name": x["name"],
            "_id": x["id"],
            "image_src": x["primaryImage"].get("url")
        }, result_json["offers"]))

        to_return = {
            "total": result_json["totalCount"],
            "count": result_json["count"],
            "offers": required_data
        }
        ToLog.write_basic(f"Allegro returned len {len(to_return)}")
        return to_return


async def update_offers_in_bulks(offers_array, access_token: str, callback_manager: CallbackManager = CallbackManager(),
                                 oferta_ids_to_process: List[str] | None = None):
    try:
        array_with_price_errors_to_update = []
        array_to_end = []
        array_to_activate = []
        failed_http_request = []

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/vnd.allegro.public.v1+json",
            "Accept": "application/vnd.allegro.public.v1+json",
        }

        current_escaped = await EscapedManager.get_current_escaped(access_token)

        async with (httpx.AsyncClient(limits=limits, timeout=timeout) as client):
            # counter = 0
            for i in range(0, len(offers_array), 50):
                batch = offers_array[i:i + 50]
                tasks = []
                for offer in batch:
                    id_ = offer.get('id')
                    if oferta_ids_to_process:
                        if id_ not in oferta_ids_to_process:
                            continue
                        else:
                            send_log = True
                    else:
                        send_log = False

                    if id_ in current_escaped:
                        ToLog.write_basic(f"Предложение {id_} обновляется в одной из Cron-Job")
                        await callback_manager.send_ok_callback_async(
                            f"Предложение {id_} обновляется в одной из Cron-Job"
                        )
                        continue
                    tasks.append(asyncio.create_task(process_offer(
                        offer, client, headers, callback_manager, 
                        array_with_price_errors_to_update, array_to_end, 
                        array_to_activate, failed_http_request, send_log
                    )))
                    # counter += 1

                await asyncio.gather(*tasks)
                # await callback_manager.send_ok_callback_async(f"Было обработано 50 предл")

        if array_with_price_errors_to_update:
            ToLog.write_basic(f"Обновление {len(array_with_price_errors_to_update)} предложений(я) с ошибками цены...")
            await callback_manager.send_ok_callback_async(
                f"Обновление {len(array_with_price_errors_to_update)} предложений(я) с ошибками цены..."
            )
            await update_offers(array_with_price_errors_to_update, access_token, callback_manager,
                                oferta_ids_to_process)
        if array_to_activate:
            ToLog.write_basic(f"Активация {len(array_to_activate)} предложений...")
            await callback_manager.send_ok_callback_async(f"Активация {len(array_to_activate)} предложений(я)...")
            await update_offers_status(access_token, array_to_activate, "ACTIVATE", callback_manager)
        if array_to_end:
            ToLog.write_basic(f"Завершение {len(array_to_end)} предложений(я) с ошибками...")
            await callback_manager.send_ok_callback_async(
                f"Завершение {len(array_to_end)} предложений(я) с ошибками..."
            )
            await update_offers_status(access_token, array_to_end, "END", callback_manager)

        if failed_http_request:
            ToLog.write_basic(
                f"Следующие позиции не удалось обновить из-за ошибки сервера: \n"
                f"{', '.join([item['id'] for item in failed_http_request])}"
            )
            await callback_manager.send_ok_callback_async(
                f"Следующие позиции не удалось обновить из-за ошибки сервера: \n"
                f"{', '.join([item['id'] for item in failed_http_request])}"
            )

    except Exception as error:
        ToLog.write_error(f"Критическая ошибка: {error}")
        await callback_manager.send_error_callback_async(f"Критическая ошибка: {error}")
        raise error


async def process_offer(offer, client, headers, callback_manager,
                        array_with_price_errors_to_update, array_to_end, array_to_activate, failed_http_request,
                        send_log=False):
    max_retries = 20
    id_ = offer.get('id')
    stock = offer.get('stock')
    price = offer.get('price')
    # weight = offer.get("weight")

    if stock == 0:
        array_to_end.append(offer)
        return

    data = {
        "sellingMode": {
            "price": {
                "amount": price,
                "currency": "PLN",
            },
        },
        "stock": {
            "available": stock,
            "unit": "UNIT",
        },
    }

    # ToLog.write_basic(f"type {type(weight)}, value {weight}")
    #
    # if isinstance(weight, (int, float)) and weight != "N/A":
    #     data.update(
    #         {
    #             "parameters": [
    #                 {
    #                     "id": 226262,
    #                     # "name": "Waga",
    #                     "values": [(weight / 1000)]
    #
    #                 }
    #             ]
    #         }
    #     )
    #     ToLog.write_basic("data updated with weight")

    url = f"https://api.allegro.pl/sale/product-offers/{id_}"
    retries = 0
    success = False

    while retries < max_retries and not success:
        try:
            response = await client.patch(url, headers=headers, json=data)
            if response.status_code in [200, 202]:
                ToLog.write_basic(f"Предложение {id_} успешно обновлено")
                if send_log:
                    await callback_manager.send_ok_callback_async(f"Предложение {id_} успешно обновлено")

                array_to_activate.append(offer)
                success = True
            else:
                await handle_errors(response, offer, array_to_end, array_with_price_errors_to_update, callback_manager)
                success = True
        except httpx.HTTPStatusError as http_err:
            status_code = http_err.response.status_code if http_err.response else None
            if status_code in [500, 501, 502, 503, 504]:
                retries += 1
                await asyncio.sleep(5)
            elif status_code in [429]:
                retries += 1
                await asyncio.sleep(60)
            else:
                await handle_errors(http_err.response, offer, array_to_end, array_with_price_errors_to_update,
                                    callback_manager)
                retries = max_retries
                success = True

    if not success:
        await callback_manager.send_ok_callback_async(f"Не удалось обновить предложение {id_}")
        failed_http_request.append(offer)


async def handle_errors(response, offer, array_to_end, array_with_price_errors_to_update,
                        callback_manager: CallbackManager):
    try:
        json_response = response.json()
    except json.JSONDecodeError:
        return

    status_code = response.status_code
    error_object = json_response['errors'][0] if json_response.get('errors') else None
    error_for_id = {
        "id": offer.get('id'),
        "errorCode": error_object.get('code') if error_object else None,
        "errorText": error_object.get('userMessage') if error_object else None,
    }

    if error_object:
        if status_code == 400 and error_object.get('code') == "IllegalOfferUpdateException.IllegalIncreasePrice":
            error_text = error_object.get('userMessage')
            regex_match = re.search(r'([0-9]+,[0-9]+) PLN', error_text)
            if regex_match:
                price_string = regex_match.group(1)
                price = math.floor(float(price_string.replace(',', '.')))
                new_price = price - 0.01
                array_with_price_errors_to_update.append(
                    {"id": offer.get('id'), "price": new_price, "stock": offer.get('stock')})
        elif status_code in [401, 403]:
            pass

        elif status_code in [404]:
            id_ = offer.get("id")
            try:
                await MongoManager.remove_position_by_allegro_id(id_)
            except Exception as e:
                ToLog.write_error(f"Error during removing offer {id_} from Mongo map\n{e}")
            else:
                ToLog.write_basic(f"Offer {id_} persistent removed from Mongo map")

        elif status_code == 422 and error_object.get('code') == "IllegalOfferUpdateException.IllegalIncreasePrice":
            error_text = error_object.get('userMessage')
            regex_match = re.search(r'([0-9]+,[0-9]+) PLN', error_text)
            if regex_match:
                price_string = regex_match.group(1)
                price = math.floor(float(price_string.replace(',', '.')))
                new_price = price - 0.01
                array_with_price_errors_to_update.append(
                    {"id": offer.get('id'), "price": new_price, "stock": offer.get('stock')})
            else:
                pass

        else:
            ToLog.write_basic(
                f"Предложение {offer.get('id')} получило ошибку {status_code}: '{error_object.get('userMessage')}'\n"
                f"Allegro error code '{error_object.get('code')}' and message '{error_object.get('message')}'"
                f"Full error: {error_object}"
            )
            await callback_manager.send_ok_callback_async(
                f"Предложение {offer.get('id')} получило ошибку {status_code}: {error_object.get('userMessage')}. "
                f"Если предложение активно, оно будет деактивировано."
            )
            array_to_end.append(error_for_id)
    else:
        ToLog.write_basic(
            f"Статус ошибки: {status_code}. Ошибка: {error_object}"
        )
        # await callback_manager.send_ok_callback_async(
        #     f"Статус ошибки: {status_code}. Ошибка: {error_object}"
        # )
        array_to_end.append(error_for_id)


async def update_offers(offers_array, access_token: str, callback_manager: CallbackManager = CallbackManager(),
                        oferta_ids_to_process: List[str] | None = None):

    try:
        array_with_price_errors_to_update = []
        array_to_end = []
        array_to_activate = []
        failed_http_request = []

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/vnd.allegro.public.v1+json",
            "Accept": "application/vnd.allegro.public.v1+json",
        }

        max_retries = 15
        async with httpx.AsyncClient() as client:
            # count = 1
            for offer in offers_array:
                id_ = offer.get('id')
                if oferta_ids_to_process and id_ not in oferta_ids_to_process:
                    continue

                # await callback_manager.send_ok_callback_async(f"{id_}. Testing logging information...")
                # count += 1
                # if count == 30:
                #     return
                stock = offer.get('stock')
                price = offer.get('price')

                #TODO
                if stock == 0:
                    ToLog.write_basic(f"Offer {id_} is 0 stock. Pushed to the arrayToEnd.")
                    array_to_end.append(offer)
                    continue

                data = {
                    "sellingMode": {
                        "price": {
                            "amount": price,
                            "currency": "PLN",
                        },
                    },
                    "stock": {
                        "available": stock,
                        "unit": "UNIT",
                    },

                }

                url = f"https://api.allegro.pl/sale/product-offers/{id_}"
                retries = 0
                success = False

                while retries < max_retries and not success:
                    try:
                        response = await client.patch(url, headers=headers, json=data)
                        if response.status_code in [200, 202]:
                            ToLog.write_basic(f"Offer {id_} updated successfully")
                            await callback_manager.send_ok_callback_async(f"Offer {id_} updated successfully")
                            array_to_activate.append(offer)
                            success = True
                        else:
                            await handle_errors(response, offer, array_to_end, array_with_price_errors_to_update,
                                                callback_manager)
                            success = True
                    except httpx.HTTPStatusError as http_err:
                        ToLog.write_error(f"HTTP error occurred: {http_err}")
                        status_code = http_err.response.status_code if http_err.response else None
                        if status_code in [500, 501, 502, 503, 504]:
                            ToLog.write_basic("Bad request - will try again in 5 seconds...")
                            retries += 1
                            await sleep(5)
                        else:
                            await handle_errors(http_err.response, offer, array_to_end,
                                                array_with_price_errors_to_update, callback_manager)
                            retries = max_retries
                            success = True

                if not success:
                    ToLog.write_basic(f"I failed to update {id_}")
                    await callback_manager.send_ok_callback_async(f"I failed to update {id_}")
                    failed_http_request.append(offer)

                ToLog.write_basic(f"Activate: {len(array_to_activate)}")
                ToLog.write_basic(f"End: {len(array_to_end)}")
                ToLog.write_basic(f"UpdatePriceErrors {len(array_with_price_errors_to_update)}")

        if array_with_price_errors_to_update:
            ToLog.write_basic(f"Updating {len(array_with_price_errors_to_update)} offers with price error...")
            await callback_manager.send_ok_callback_async(
                f"Updating {len(array_with_price_errors_to_update)} offers with price error..."
            )
            await update_offers(array_with_price_errors_to_update, access_token, callback_manager,
                                oferta_ids_to_process)
        if array_to_activate:
            ToLog.write_basic(f"Activating {len(array_to_activate)} offers...")
            await callback_manager.send_ok_callback_async(f"Activating {len(array_to_activate)} offers...")
            await update_offers_status(access_token, array_to_activate, "ACTIVATE", callback_manager)
        if array_to_end:
            ToLog.write_basic(f"Finishing {len(array_to_end)} offers with errors...")
            await callback_manager.send_ok_callback_async(f"Finishing {len(array_to_end)} offers with errors...")
            await update_offers_status(access_token, array_to_end, "END", callback_manager)

        ToLog.write_basic(f"Here are the items that could not be updated due to a server error: {failed_http_request}")
        await callback_manager.send_ok_callback_async(
            f"Here are the items that could not be updated due to a server error: \n"
            f"{', '.join([item.id_ for item in failed_http_request])}"
        )
    except Exception as error:
        ToLog.write_error(f"Critical error: {error}")
        await callback_manager.send_error_callback_async(f"Critical error: {error}")
        # await send_telegram_message(f"Critical error in update_offers function: {error}")
        raise error


async def update_offers_status(access_token, offers, action, callback_manager: CallbackManager):
    batch_size = 1000
    max_offers_per_minute = 3000
    start_index = 0

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/vnd.allegro.public.v1+json',
        'Content-Type': 'application/vnd.allegro.public.v1+json'
    }

    async with httpx.AsyncClient() as client:
        while start_index < len(offers):
            end_index = min(start_index + batch_size, len(offers))
            batch_offers = offers[start_index:end_index]

            payload = {
                "offerCriteria": [
                    {
                        "offers": [{"id": offer.get('id')} for offer in batch_offers],
                        "type": "CONTAINS_OFFERS",
                    }
                ],
                "publication": {
                    "action": action,
                },
            }

            command_id = str(uuid.uuid4())
            url = f"https://api.allegro.pl/sale/offer-publication-commands/{command_id}"

            try:
                response = await client.put(url, headers=headers, json=payload)
                if response.status_code == 201:
                    ToLog.write_basic(
                        f"Команда {action} успешно выполнена. Command ID: {command_id}."
                    )
                    await callback_manager.send_ok_callback_async(
                        f"Команда {action} успешно выполнена. Command ID: {command_id}.\n"
                        f"Потребуется время для применения изменений"
                    )
                else:
                    ToLog.write_basic(
                        f"Ошибка {response.status_code}: {response.text}"
                    )
                    await callback_manager.send_error_callback_async(
                        f"Ошибка {response.status_code}: {response.text}"
                    )
            except Exception as error:
                ToLog.write_error(f"Ошибка отправки запроса: {error}")
                await callback_manager.send_error_callback_async(f"Ошибка отправки запроса: {error}")

            start_index += batch_size

            if start_index % max_offers_per_minute == 0:
                ToLog.write_basic(
                    "Ожидание 1 минуту перед обработкой следующих предложений..."
                )
                await callback_manager.send_ok_callback_async(
                    "Ожидание 1 минуту перед обработкой следующих предложений..."
                )
                await asyncio.sleep(60)
            else:
                await asyncio.sleep(0.5)


def update_offers_sync(offers_array, access_token: str, callback_manager: CallbackManager = CallbackManager(),
                       oferta_ids_to_process: List[str] = None):
    try:
        array_with_price_errors_to_update = []
        array_to_end = []
        array_to_activate = []
        failed_http_request = []

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/vnd.allegro.public.v1+json",
            "Accept": "application/vnd.allegro.public.v1+json",
        }

        max_retries = 5
        for offer in offers_array:
            id_ = offer.get('id')

            if oferta_ids_to_process and id_ not in oferta_ids_to_process:
                continue

            stock = offer.get('stock')
            price = offer.get('price')

            if stock == 0:
                ToLog.write_basic(f"Offer {id_} is 0 stock. Pushed to the arrayToEnd.")
                array_to_end.append(offer)
                continue

            data = {
                "sellingMode": {
                    "price": {
                        "amount": price,
                        "currency": "PLN",
                    },
                },
                "stock": {
                    "available": stock,
                    "unit": "UNIT",
                },
            }

            url = f"https://api.allegro.pl/sale/product-offers/{id_}"
            retries = 0
            success = False

            while retries < max_retries and not success:
                try:
                    response = requests.patch(url, headers=headers, json=data)
                    if response.status_code in [200, 202]:
                        ToLog.write_basic(f"Offer {id_} updated successfully")
                        callback_manager.send_ok_callback(f"Offer {id_} updated successfully")
                        array_to_activate.append(offer)
                        success = True
                    else:
                        handle_errors_sync(response, offer, array_to_end, array_with_price_errors_to_update)
                        success = True
                except requests.RequestException as req_err:
                    ToLog.write_error(f"HTTP error occurred: {req_err}")
                    status_code = req_err.response.status_code if req_err.response else None
                    if status_code in [500, 501, 502, 503, 504]:
                        ToLog.write_basic("Bad request - will try again in 5 seconds...")
                        retries += 1
                        time.sleep(5)
                    else:
                        handle_errors_sync(req_err.response, offer, array_to_end, array_with_price_errors_to_update)
                        retries = max_retries
                        success = True

            if not success:
                ToLog.write_basic(f"I failed to update {id_}")
                callback_manager.send_ok_callback(f"I failed to update {id_}")
                failed_http_request.append(offer)

        ToLog.write_basic(f"Activate: {len(array_to_activate)}")
        ToLog.write_basic(f"End: {len(array_to_end)}")
        ToLog.write_basic(f"UpdatePriceErrors {len(array_with_price_errors_to_update)}")

        if array_with_price_errors_to_update:
            ToLog.write_basic(f"Updating {len(array_with_price_errors_to_update)} offers with price error...")
            callback_manager.send_ok_callback(
                f"Updating {len(array_with_price_errors_to_update)} offers with price error...")
            update_offers_sync(array_with_price_errors_to_update, access_token, callback_manager, oferta_ids_to_process)
        if array_to_activate:
            ToLog.write_basic(f"Activating {len(array_to_activate)} offers...")
            callback_manager.send_ok_callback(f"Activating {len(array_to_activate)} offers...")
            update_offers_status_sync(access_token, array_to_activate, "ACTIVATE", callback_manager)
        if array_to_end:
            ToLog.write_basic(f"Finishing {len(array_to_end)} offers with errors...")
            callback_manager.send_ok_callback(f"Finishing {len(array_to_end)} offers with errors...")
            update_offers_status_sync(access_token, array_to_end, "END", callback_manager)

        ToLog.write_basic(f"Here are the items that could not be updated due to a server error: {failed_http_request}")
        callback_manager.send_error_callback(f"Here are the items that could not be updated due to a server error: \n"
                                             f"{', '.join([item['id'] for item in failed_http_request])}")
    except Exception as error:
        ToLog.write_error(f"Critical error: {error}")
        callback_manager.send_error_callback(f"Critical error: {error}")
        raise error
    
    
def handle_errors_sync(response, offer, array_to_end, array_with_price_errors_to_update):
    try:
        json_response = response.json()
    except json.JSONDecodeError:
        ToLog.write_error("Unknown error: empty error object")
        return

    status_code = response.status_code
    error_object = json_response['errors'][0] if json_response.get('errors') else None
    error_for_id = {
        "id": offer.get('id'),
        "errorCode": error_object.get('code') if error_object else None,
        "errorText": error_object.get('userMessage') if error_object else None,
    }

    if error_object:
        if status_code == 400 and error_object.get('code') == "IllegalOfferUpdateException.IllegalIncreasePrice":
            error_text = error_object.get('userMessage')
            regex_match = re.search(r'([0-9]+,[0-9]+) PLN', error_text)
            if regex_match:
                price_string = regex_match.group(1)
                price = math.floor(float(price_string.replace(',', '.')))
                new_price = price - 0.01
                array_with_price_errors_to_update.append(
                    {"id": offer.get('id'), "price": new_price, "stock": offer.get('stock')})
        elif status_code in [401, 403]:
            ToLog.write_error(f"Error code {status_code}: {error_object.get('userMessage')}")
        elif status_code == 422 and error_object.get('code') == "IllegalOfferUpdateException.IllegalIncreasePrice":
            error_text = error_object.get('userMessage')
            regex_match = re.search(r'([0-9]+,[0-9]+) PLN', error_text)
            if regex_match:
                price_string = regex_match.group(1)
                price = math.floor(float(price_string.replace(',', '.')))
                new_price = price - 0.01
                array_with_price_errors_to_update.append(
                    {"id": offer.get('id'), "price": new_price, "stock": offer.get('stock')})
                ToLog.write_basic(f"New price for {offer.get('id')} is {new_price}.")
            else:
                ToLog.write_basic("Failed to parse the price!")
        else:
            ToLog.write_basic(
                f"Offer {offer.get('id')} got an error code {status_code}: {error_object.get('userMessage')}")
            array_to_end.append(error_for_id)
    else:
        ToLog.write_basic(f"Error status code: {status_code}. Error: {error_object}")
        array_to_end.append(error_for_id)


def update_offers_status_sync(access_token, offers, action, callback_manager):
    batch_size = 1000
    max_offers_per_minute = 9000
    start_index = 0

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/vnd.allegro.public.v1+json',
        'Content-Type': 'application/vnd.allegro.public.v1+json'
    }

    while start_index < len(offers):
        end_index = min(start_index + batch_size, len(offers))
        batch_offers = offers[start_index:end_index]

        payload = {
            "offerCriteria": [
                {
                    "offers": [{"id": offer.get('id')} for offer in batch_offers],
                    "type": "CONTAINS_OFFERS",
                }
            ],
            "publication": {
                "action": action,
            },
        }

        command_id = str(uuid.uuid4())
        url = f"https://api.allegro.pl/sale/offer-publication-commands/{command_id}"

        try:
            response = requests.put(url, headers=headers, json=payload)
            if response.status_code == 201:
                ToLog.write_basic(f"Command {action}ed successfully. Command ID: {command_id}. {response.text}")
                callback_manager.send_ok_callback(f"Command {action}ed successfully. Command ID: {command_id}. {response.text}")
            else:
                ToLog.write_basic(f"Error {response.status_code}: {response.text}")
                callback_manager.send_error_callback(f"Error {response.status_code}: {response.text}")
        except Exception as error:
            ToLog.write_error(f"Error sending request: {error}")
            callback_manager.send_error_callback(f"Error sending request: {error}")

        start_index += batch_size

        if start_index % max_offers_per_minute == 0:
            ToLog.write_basic("Waiting for 1 minute before processing more offers...")
            callback_manager.send_ok_callback("Waiting for 1 minute before processing more offers...")
            time.sleep(60)
        else:
            time.sleep(0.5)


async def search_product_by_ean_return_first(ean, access_token):

    url = f"https://api.allegro.pl/sale/products"
    params = {
        "phrase": ean,
        "mode": "GTIN"
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/vnd.allegro.public.v1+json",
        "Accept": "application/vnd.allegro.public.v1+json",
    }

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        result = await client.get(url=url, headers=headers, params=params)
        if result.status_code in [429]:
            await asyncio.sleep(60)
            result = await client.get(url=url, headers=headers, params=params)

        products = result.json()["products"]
        if products:
            return products[0]
        return []


async def create_single_offer(product, access_token):

    url = f"https://api.allegro.pl/sale/product-offers"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/vnd.allegro.public.v1+json",
        "Accept": "application/vnd.allegro.public.v1+json",
    }
    params = {
        "productSet": [
            {
                "product": {"id": product["allegro_product_id"]},
            }
        ],
        "stock": {
            "available": product["stock"],
            "unit": "UNIT"
        },
        "language": "pl-PL",
        "category": {"id": product["category_id"]},
        "name": product["product_name"],
        "sellingMode": {
            "format": "BUY_NOW",
            "price": {
                "amount": product["price"],
                "currency": "PLN"
            },
        },
        "external": {"id": product['product_sku']}
    }
    new_params = json.dumps(params)

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        result = await client.post(url=url, headers=headers, data=new_params)
    if result.status_code in [429]:
        await asyncio.sleep(60)
        result = await client.post(url=url, headers=headers, data=new_params)

    if result.status_code in [201, 202]:
        return result.json()



def sleep(ms):
    return asyncio.sleep(ms / 1000)








