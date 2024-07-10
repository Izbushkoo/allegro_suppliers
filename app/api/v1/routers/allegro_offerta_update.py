import asyncio
import os
from typing import Any, List, Dict

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, WebSocket
import jwt
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.websockets import WebSocketDisconnect
from pydantic import BaseModel

from app.api import deps
from app.services.updates import get_all_data, fetch_and_update_allegro, \
    fetch_and_update_allegro_bulks, get_all_data_current_test
from app.services.modules.APITokenManager import check_token
from app.services.modules.AlegroApiManager import get_page_offers, update_offers_status

from app.services.modules.DatabaseManager import MongoManager
from app.core.bg_task_wrapper import TaskWrapper
from app.schemas.pydantic_models import UpdateConfig, CallbackManager, OffersRequest, UpdateOffersRequest
from app.services.allegro_token import get_token_by_id
from app.loggers import ToLog


router = APIRouter(dependencies=[Depends(deps.get_api_token)])
ws_router = APIRouter()


supplier_name = {
    "pgn": "pgn",
    "unimet": "unimet",
    "hurtprem": "hurtprem",
    "rekman": "rekman",
    "growbox": "growbox"
}


@router.get("/test")
async def update_suppliers_test_parse(supplier: str):
    fil_obj = await get_all_data_current_test(supplier)

    ToLog.write_basic("succsess")

    return list(fil_obj.items())[-1]


# @router.post("/update")
# async def update_suppliers(request: Request, update_config: UpdateConfig, bg_tasks: BackgroundTasks):
#     """Обновить Аллегро оферты для заданного аккаунта.
#     Доступные поставщики: "pgn", "unimet", "hurtprem", "rekman", "growbox". В случае отсутствия в конфиге списка
#     поставщиков, обновление произойдет для всех доступных.
#     То же самое в случае с переданным параметром 'oferta_ids_to_process'. В случае отсутствия обработка произойдет
#     для всех товаров.
#     """
#     try:
#         if update_config.resource_id is None:
#             raise ValueError("RESOURCE_ID не должен быть None")
#         if update_config.callback_url is None:
#             raise ValueError("CALLBACK_URL не должен быть None")
#
#         os.environ["RESOURCE_ID"] = update_config.resource_id
#         os.environ["CALLBACK_URL"] = update_config.callback_url
#     except Exception as e:
#         ToLog.write_error(f"{e}")
#
#     ToLog.write_access(f"Access to update supplier with request: {await request.json()}")
#     bg_tasks.add_task(
#         TaskWrapper(task=update_as_task).run_task(
#             update_config=update_config
#         )
#     )
#     return JSONResponse({"status": "OK", "message": "Update task started"})


@router.post("/update_bulks")
async def update_suppliers(request: Request, update_config: UpdateConfig, bg_tasks: BackgroundTasks):
    """Обновить Аллегро оферты для заданного аккаунта.
    Доступные поставщики: "pgn", "unimet", "hurtprem", "rekman", "growbox". В случае отсутствия в конфиге списка
    поставщиков, обновление произойдет для всех доступных.
    То же самое в случае с переданным параметром 'oferta_ids_to_process'. В случае отсутствия обработка произойдет
    для всех товаров.
    """
    try:
        if update_config.resource_id is None:
            raise ValueError("RESOURCE_ID не должен быть None")
        if update_config.callback_url is None:
            raise ValueError("CALLBACK_URL не должен быть None")

        os.environ["RESOURCE_ID"] = update_config.resource_id
        os.environ["CALLBACK_URL"] = update_config.callback_url
    except Exception as e:
        ToLog.write_error(f"{e}")

    ToLog.write_access(f"Access to update supplier with request: {await request.json()}")
    bg_tasks.add_task(
        TaskWrapper(task=update_as_task_in_bulks).run_task(
            update_config=update_config
        )
    )
    return JSONResponse({"status": "OK", "message": "Update task started"})


@router.post("/get_offers")
async def get_offers_by_name(request: Request, offers_request: OffersRequest,
                             database: AsyncSession = Depends(deps.get_db_async)):
    """Роут возвращает JSON содержащий оферты Title которых включает заданную фразу
    В теле запроса параметры по умолчанию offset - 0 и limit - 500. Это сделано для того чтобы не перегружать ответ
    в случаях когда оферт слишком много.
    """

    ToLog.write_access(f"Access to get offers with request: {await request.json()}")
    allegro_token = await get_token_by_id(database, offers_request.token_id)

    try:
        token = await check_token(database, allegro_token)
    except Exception as err:
        ToLog.write_error(f"Error while check and update token {err}")
        return HTTPException(status_code=403, detail=f"Error while check and update token {err}")
    else:
        access_token = token.access_token

    result = await get_page_offers(offers_request, access_token)

    return result


@router.patch("/update_offers_status")
async def delete_from_map(request: Request, update_offers_request: UpdateOffersRequest,
                          bg_tasks: BackgroundTasks, database: AsyncSession = Depends(deps.get_db_async)):

    callback_manager = CallbackManager(
        url=update_offers_request.callback_url,
        resource_id=update_offers_request.resource_id
    )
    ToLog.write_access(f"Access to delete offers with request: {await request.json()}")
    allegro_token = await get_token_by_id(database, update_offers_request.token_id)

    try:
        token = await check_token(database, allegro_token)
    except Exception as err:
        ToLog.write_error(f"Error while check and update token {err}")
        return HTTPException(status_code=403, detail=f"Error while check and update token {err}")
    else:
        access_token = token.access_token
    try:
        sell = True if update_offers_request.action == "ACTIVATE" else False
        await MongoManager.set_we_sell_to(
            update_offers_request.oferta_ids,
            sell
        )
    except Exception as e:
        ToLog.write_error(f"Error during '.set_we_sell_to_...()' from Mongo map {e}")
    else:
        await callback_manager.send_ok_callback_async(
            f"Предложения были успешно обновлены 'allegro_we_sell_it': {sell} в Mongo Map")
        ToLog.write_basic(f"Предложения были успешно обновлены 'allegro_we_sell_it': {sell} в Mongo Map")

    bg_tasks.add_task(
        TaskWrapper(task=update_status_on_allegro_as_task).run_task(
            update_offers_request=update_offers_request,
            access_token=access_token
        )
    )

    return JSONResponse({"status": "OK", "message": "Activate/Deactivate task started"})


async def update_status_on_allegro_as_task(update_offers_request: UpdateOffersRequest, access_token: str):
    callback_manager = CallbackManager(
        url=update_offers_request.callback_url,
        resource_id=update_offers_request.resource_id
    )
    if update_offers_request.action in ["ACTIVATE", "END"]:
        offers = [{"id": item} for item in update_offers_request.oferta_ids]
        await update_offers_status(access_token, offers, update_offers_request.action, callback_manager)
        await callback_manager.send_finish_callback_async(f"Завершено для {len(offers)}")
    else:
        await callback_manager.send_error_callback_async(
            f"Действие '{update_offers_request.action}' недопустимо. Не выполнено."
        )


async def update_as_task(update_config: UpdateConfig):

    callback_manager = CallbackManager(
        url=update_config.callback_url,
        resource_id=update_config.resource_id
    )
    ToLog.write_basic(f"callback manager {callback_manager.model_dump()}")

    database = deps.AsyncSessLocal()
    allegro_token = await get_token_by_id(database, update_config.allegro_token_id)
    multiplier = update_config.multiplier
    oferta_ids_to_process = update_config.oferta_ids_to_process

    suppliers_list = update_config.suppliers_to_update if update_config.suppliers_to_update else list(
        supplier_name.values()
    )

    ToLog.write_basic(f"{suppliers_list}")
    for supplier in suppliers_list:
        try:
            await callback_manager.send_ok_callback_async(f"Start to download {supplier} data.")
            filtered_objects = await get_all_data(supplier, True, multiplier)
        except Exception as e:
            await callback_manager.send_error_callback_async(f"Error with parsing {supplier} data. Try later.")
            ToLog.write_error(f"{e}")
        else:
            await callback_manager.send_ok_callback_async(f"Data downloaded and parsed successfully for {supplier}")
            await fetch_and_update_allegro(
                database,
                filtered_objects,
                allegro_token,
                oferta_ids_to_process=oferta_ids_to_process,
                callback_manager=callback_manager
            )

    ToLog.write_basic("Update Finished")
    await callback_manager.send_finish_callback_async("Update Finished")


async def update_as_task_in_bulks(update_config: UpdateConfig, **kwargs):

    semaphore = kwargs.get("semaphore")
    if not semaphore:
        semaphore = asyncio.Semaphore(1)

    async with semaphore:
        callback_manager = CallbackManager(
            url=update_config.callback_url,
            resource_id=update_config.resource_id
        )
        ToLog.write_basic(f"callback manager {callback_manager.model_dump()}")

        database = deps.AsyncSessLocal()
        allegro_token = await get_token_by_id(database, update_config.allegro_token_id)

        try:
            await callback_manager.send_ok_callback_async(
                f"Проверяем валидность токена '{allegro_token.account_name}'..."
            )
            token = await check_token(database, allegro_token, callback_manager)
        except Exception as err:
            ToLog.write_error(f"Error while check and update token {err}")
            await callback_manager.send_error_callback(f"Ошибка во время проверки и обновления токена: {err}")
            return
        else:
            access_token = token.access_token

        multiplier = update_config.multiplier
        oferta_ids_to_process = update_config.oferta_ids_to_process
        suppliers_list = update_config.suppliers_to_update if update_config.suppliers_to_update else list(
            supplier_name.values()
        )

        for i in range(0, len(suppliers_list), 2):
            batch = suppliers_list[i:i + 2]
            tasks = []

            for supplier in batch:
                task = asyncio.create_task(
                    update_single_supplier(
                        supplier, multiplier, access_token, oferta_ids_to_process, callback_manager
                    )
                )
                tasks.append(task)
            await asyncio.gather(*tasks)

        ToLog.write_basic("Update Finished")
        await callback_manager.send_finish_callback_async("Обновление завершено.")


async def update_single_supplier(supplier: str, multiplier: float | int, access_token, oferta_ids_to_process,
                                 callback_manager: CallbackManager):

    try:
        await callback_manager.send_ok_callback_async(f"Начинаем скачивание данных для {supplier}")
        filtered_objects = await get_all_data(supplier, True, multiplier,
                                              callback_manager)
    except Exception as e:
        await callback_manager.send_error_callback_async(f"Ошибка во время парсинга данных для {supplier}. "
                                                         f"Попробуйте позже.")
        ToLog.write_error(f"{e}")
    else:
        await callback_manager.send_ok_callback_async(f"Данные загружены и распаршены успешно для: {supplier}")
        await fetch_and_update_allegro_bulks(
            filtered_objects,
            access_token,
            oferta_ids_to_process=oferta_ids_to_process,
            callback_manager=callback_manager
        )





