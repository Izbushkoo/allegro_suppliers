import json
import uuid
import math
import asyncio
import re
import os
from typing import List

import httpx

from app.loggers import ToLog
from app.schemas.pydantic_models import ConfigManager, ConnectionManager, CallbackManager

# async def send_telegram_message(message):
#     bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
#     chat_id = os.getenv('TELEGRAM_CHAT_ID')
#     url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={message}"
#
#     async with httpx.AsyncClient() as client:
#         try:
#             response = await client.get(url)
#             json_response = response.json()
#             if json_response['ok']:
#                 print(f"Telegram message sent successfully: {message}")
#             else:
#                 print(f"Error sending Telegram message: {json_response['description']}")
#         except Exception as error:
#             print(f"Error sending Telegram message: {error}")


async def update_offers(offers_array, access_token: str, callback_manager: CallbackManager,
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

        max_retries = 5
        async with httpx.AsyncClient() as client:
            for offer in offers_array:
                id_ = offer.get('id')
                if oferta_ids_to_process and id_ not in oferta_ids_to_process:
                    continue

        #         stock = offer.get('stock')
        #         price = offer.get('price')
        #
        #         #TODO
        #         if stock == 0:
        #             ToLog.write_basic(f"Offer {id_} is 0 stock. Pushed to the arrayToEnd.")
        #             array_to_end.append(offer)
        #             continue
        #
        #         data = {
        #             "sellingMode": {
        #                 "price": {
        #                     "amount": price,
        #                     "currency": "PLN",
        #                 },
        #             },
        #             "stock": {
        #                 "available": stock,
        #                 "unit": "UNIT",
        #             },
        #         }
        #
        #         url = f"https://api.allegro.pl/sale/product-offers/{id_}"
        #         retries = 0
        #         success = False
        #
        #         while retries < max_retries and not success:
        #             try:
        #                 response = await client.patch(url, headers=headers, json=data)
        #                 if response.status_code in [200, 202]:
        #                     ToLog.write_basic(f"Offer {id_} updated successfully")
        #                     await callback_manager.send_ok_callback_async(f"Offer {id_} updated successfully")
        #                     array_to_activate.append(offer)
        #                     success = True
        #                 else:
        #                     await handle_errors(response, offer, array_to_end, array_with_price_errors_to_update)
        #                     success = True
        #             except httpx.HTTPStatusError as http_err:
        #                 ToLog.write_error(f"HTTP error occurred: {http_err}")
        #                 status_code = http_err.response.status_code if http_err.response else None
        #                 if status_code in [500, 501, 502, 503, 504]:
        #                     ToLog.write_basic("Bad request - will try again in 5 seconds...")
        #                     retries += 1
        #                     await sleep(5)
        #                 else:
        #                     await handle_errors(http_err.response, offer, array_to_end,
        #                                         array_with_price_errors_to_update)
        #                     retries = max_retries
        #                     success = True
        #
        #         if not success:
        #             ToLog.write_basic(f"I failed to update {id_}")
        #             await callback_manager.send_ok_callback_async(f"I failed to update {id_}")
        #             failed_http_request.append(offer)
        #
        #         ToLog.write_basic(f"Activate: {len(array_to_activate)}")
        #         ToLog.write_basic(f"End: {len(array_to_end)}")
        #         ToLog.write_basic(f"UpdatePriceErrors {len(array_with_price_errors_to_update)}")
        #
        # if array_with_price_errors_to_update:
        #     ToLog.write_basic(f"Updating {len(array_with_price_errors_to_update)} offers with price error...")
        #     await callback_manager.send_ok_callback_async(
        #         f"Updating {len(array_with_price_errors_to_update)} offers with price error..."
        #     )
        #     await update_offers(array_with_price_errors_to_update, access_token, callback_manager,
        #                         oferta_ids_to_process)
        # if array_to_activate:
        #     ToLog.write_basic(f"Activating {len(array_to_activate)} offers...")
        #     await callback_manager.send_ok_callback_async(f"Activating {len(array_to_activate)} offers...")
        #     await update_offers_status(access_token, array_to_activate, "ACTIVATE", callback_manager)
        # if array_to_end:
        #     ToLog.write_basic(f"Finishing {len(array_to_end)} offers with errors...")
        #     await callback_manager.send_ok_callback_async(f"Finishing {len(array_to_end)} offers with errors...")
        #     await update_offers_status(access_token, array_to_end, "END", callback_manager)
        #
        # ToLog.write_basic(f"Here are the items that could not be updated due to a server error: {failed_http_request}")
        # await callback_manager.send_error_callback_async(
        #     f"Here are the items that could not be updated due to a server error: \n"
        #     f"{', '.join([item.id_ for item in failed_http_request])}"
        # )
    except Exception as error:
        ToLog.write_error(f"Critical error: {error}")
        await callback_manager.send_error_callback_async(f"Critical error: {error}")
        # await send_telegram_message(f"Critical error in update_offers function: {error}")
        raise error


async def handle_errors(response, offer, array_to_end, array_with_price_errors_to_update,
                        ):
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
            ToLog.write_basic(f"Offer {offer.get('id')} got an error code {status_code}: {error_object.get('userMessage')}")
            array_to_end.append(error_for_id)
    else:
        ToLog.write_basic(f"Error status code: {status_code}. Error: {error_object}")
        array_to_end.append(error_for_id)


async def update_offers_status(access_token, offers, action, callback_manager: CallbackManager):
    batch_size = 1000
    max_offers_per_minute = 9000
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
                    ToLog.write_basic(f"Command {action}ed successfully. Command ID: {command_id}. {response.text}")
                    await callback_manager.send_ok_callback_async(
                        f"Command {action}ed successfully. Command ID: {command_id}. {response.text}"
                    )
                else:
                    ToLog.write_basic(f"Error {response.status_code}: {response.text}")
                    await callback_manager.send_error_callback_async(
                        f"Error {response.status_code}: {response.text}"
                    )
            except Exception as error:
                ToLog.write_error(f"Error sending request: {error}")
                await callback_manager.send_error_callback_async(f"Error sending request: {error}")

            start_index += batch_size

            if start_index % max_offers_per_minute == 0:
                ToLog.write_basic("Waiting for 1 minute before processing more offers...")
                await callback_manager.send_ok_callback_async("Waiting for 1 minute before processing more offers...")

                await sleep(60000)
            else:
                await sleep(500)


async def update_offers_websocket(offers_array, access_token: str, config: ConfigManager,
                                  oferta_ids_to_process: List[str] | None = None):
    socket_manager: ConnectionManager = config.manager
    client_id = config.client_id

    try:
        array_with_price_errors_to_update = []
        array_to_end = []
        array_to_activate = []
        failed_http_request = []

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/vnd.allegro.public.v1+json",
            "Accept": "application/vnd.allegro.public.v1+json", }

        max_retries = 5
        async with httpx.AsyncClient() as client:
            for offer in offers_array:
                id_ = offer.get('id')
                if oferta_ids_to_process and id_ not in oferta_ids_to_process:
                    continue
                stop_event = socket_manager.stops.get(client_id)
                if stop_event and stop_event.is_set():
                    await socket_manager.send_personal_message(
                        {"status": "OK",
                         "message": "Updating stopped"},
                        client_id
                    )
                    socket_manager.set_task_status(client_id, "stopped")
                    return
                await sleep(5000)
        #         stock = offer.get('stock')
        #         price = offer.get('price')
        #
        #         #TODO
        #         if stock == 0:
        #             ToLog.write_basic(f"Offer {id_} is 0 stock. Pushed to the arrayToEnd.")
        #             array_to_end.append(offer)
        #             continue
        #
        #         data = {
        #             "sellingMode": {
        #                 "price": {
        #                     "amount": price,
        #                     "currency": "PLN",
        #                 },
        #             },
        #             "stock": {
        #                 "available": stock,
        #                 "unit": "UNIT",
        #             },
        #         }
        #
        #         url = f"https://api.allegro.pl/sale/product-offers/{id_}"
        #         retries = 0
        #         success = False
        #
        #         while retries < max_retries and not success:
        #             try:
        #                 response = await client.patch(url, headers=headers, json=data)
        #                 if response.status_code in [200, 202]:
        #                     ToLog.write_basic(f"Offer {id_} updated successfully")
        #                     await socket_manager.send_personal_message(
        #                         {
        #                             "status": "OK",
        #                             "message": f"Offer {id_} updated successfully"
        #                         }, client_id
        #                     )
        #                     array_to_activate.append(offer)
        #                     success = True
        #                 else:
        #                     await handle_errors_websocket(response, offer, array_to_end,
        #                                                   array_with_price_errors_to_update, config)
        #                     success = True
        #             except httpx.HTTPStatusError as http_err:
        #                 ToLog.write_error(f"HTTP error occurred: {http_err}")
        #                 status_code = http_err.response.status_code if http_err.response else None
        #                 if status_code in [500, 501, 502, 503, 504]:
        #                     ToLog.write_basic("Bad request - will try again in 5 seconds...")
        #                     retries += 1
        #                     await sleep(5)
        #                 else:
        #                     await handle_errors_websocket(http_err.response, offer, array_to_end,
        #                                                   array_with_price_errors_to_update, config)
        #                     retries = max_retries
        #                     success = True
        #
        #         if not success:
        #             ToLog.write_basic(f"I failed to update {id_}")
        #             await socket_manager.send_personal_message(
        #                 {
        #                     "status": "error",
        #                     "message": f"Failed to update {id_}"
        #                 }, client_id
        #             )
        #             failed_http_request.append(offer)
        #
        #         ToLog.write_basic(f"Activate: {len(array_to_activate)}")
        #         ToLog.write_basic(f"End: {len(array_to_end)}")
        #         ToLog.write_basic(f"UpdatePriceErrors {len(array_with_price_errors_to_update)}")
        #
        # if array_with_price_errors_to_update:
        #     ToLog.write_basic(f"Updating {len(array_with_price_errors_to_update)} offers with price error...")
        #     await update_offers_websocket(array_with_price_errors_to_update, access_token, config)
        # if array_to_activate:
        #     ToLog.write_basic(f"Activating {len(array_to_activate)} offers...")
        #     await update_offers_status(access_token, array_to_activate, "ACTIVATE")
        # if array_to_end:
        #     ToLog.write_basic(f"Finishing {len(array_to_end)} offers with errors...")
        #     await update_offers_status(access_token, array_to_end, "END")
        #
        # ToLog.write_basic(f"Here are the items that could not be updated due to a server error: {failed_http_request}")

    except Exception as error:
        await socket_manager.send_personal_message(
            {
                "status": "error",
                "message": f"Critical error: {error}"
            }, client_id
        )
        ToLog.write_error(f"Critical error: {error}")
        # await send_telegram_message(f"Critical error in update_offers function: {error}")
        raise error


async def handle_errors_websocket(response, offer, array_to_end, array_with_price_errors_to_update, config):

    socket_manager: ConnectionManager = config.manager
    client_id = config.client_id

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
            ToLog.write_basic(f"Offer {offer.get('id')} got an error code {status_code}: {error_object.get('userMessage')}")

            array_to_end.append(error_for_id)
    else:
        await socket_manager.send_personal_message(
            {
                "status": "OK",
                "message": f"Error status code: {status_code}. Error: {error_object}. Pushed to array_to_end."
            }, client_id
        )
        ToLog.write_basic(f"Error status code: {status_code}. Error: {error_object}")
        array_to_end.append(error_for_id)


def sleep(ms):
    return asyncio.sleep(ms / 1000)
