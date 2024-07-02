import asyncio
import os
from typing import Any, List, Dict

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, WebSocket
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.websockets import WebSocketDisconnect
from pydantic import BaseModel

from app.api import deps
from app.services.updates import get_all_data, fetch_and_update_allegro, get_all_data_test, \
    fetch_and_update_allegro_bulks
from app.services.modules.APITokenManager import check_token
from app.core.bg_task_wrapper import TaskWrapper
from app.schemas.pydantic_models import UpdateConfig, CallbackManager
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


@ws_router.post("/test")
async def update_suppliers_test_parse(supplier: str):
    fil_obj = await get_all_data_test(supplier, True, 1)

    ToLog.write_basic("succsess")
    return fil_obj[-1]


@router.post("/update")
async def update_suppliers(request: Request, update_config: UpdateConfig, bg_tasks: BackgroundTasks):
    """Обновить Аллегро оферты для заданного аккаунта.
    Доступные поставщики: "pgn", "unimet", "hurtprem", "rekman", "growbox". В случае отсутствия в конфиге списка
    поставщиков, обновление произойдет для всех доступных.
    То же самое в случае с переданным параметром 'oferta_ids_to_process'. В случае отсутствия обработка произойдет
    для всех товаров.
    """
    os.environ["RESOURCE_ID"] = update_config.resource_id
    os.environ["CALLBACK_URL"] = update_config.callback_url

    ToLog.write_access(f"Access to update supplier with request: {await request.json()}")
    bg_tasks.add_task(
        TaskWrapper(task=update_as_task).run_task(
            update_config=update_config
        )
    )
    return JSONResponse({"status": "OK", "message": "Update task started"})


@router.post("/update_bulks")
async def update_suppliers(request: Request, update_config: UpdateConfig, bg_tasks: BackgroundTasks):
    """Обновить Аллегро оферты для заданного аккаунта.
    Доступные поставщики: "pgn", "unimet", "hurtprem", "rekman", "growbox". В случае отсутствия в конфиге списка
    поставщиков, обновление произойдет для всех доступных.
    То же самое в случае с переданным параметром 'oferta_ids_to_process'. В случае отсутствия обработка произойдет
    для всех товаров.
    """
    os.environ["RESOURCE_ID"] = update_config.resource_id
    os.environ["CALLBACK_URL"] = update_config.callback_url

    ToLog.write_access(f"Access to update supplier with request: {await request.json()}")
    bg_tasks.add_task(
        TaskWrapper(task=update_as_task_in_bulks).run_task(
            update_config=update_config
        )
    )
    return JSONResponse({"status": "OK", "message": "Update task started"})


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


async def update_as_task_in_bulks(update_config: UpdateConfig):

    callback_manager = CallbackManager(
        url=update_config.callback_url,
        resource_id=update_config.resource_id
    )
    ToLog.write_basic(f"callback manager {callback_manager.model_dump()}")

    database = deps.AsyncSessLocal()
    allegro_token = await get_token_by_id(database, update_config.allegro_token_id)

    try:
        token = await check_token(database, allegro_token, callback_manager)
    except Exception as err:
        ToLog.write_error(f"Error while check and update token {err}")
        await callback_manager.send_error_callback(f"Error while check and update token {err}")
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
    await callback_manager.send_finish_callback_async("Update Finished")


async def update_single_supplier(supplier: str, multiplier: float | int, access_token, oferta_ids_to_process,
                                 callback_manager: CallbackManager):

    try:
        await callback_manager.send_ok_callback_async(f"Start to download {supplier} data.")
        filtered_objects = await get_all_data(supplier, True, multiplier)
    except Exception as e:
        await callback_manager.send_error_callback_async(f"Error with parsing {supplier} data. Try later.")
        ToLog.write_error(f"{e}")
    else:
        await callback_manager.send_ok_callback_async(f"Data downloaded and parsed successfully for {supplier}")
        await fetch_and_update_allegro_bulks(
            filtered_objects,
            access_token,
            oferta_ids_to_process=oferta_ids_to_process,
            callback_manager=callback_manager
        )





