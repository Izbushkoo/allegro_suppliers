import asyncio
from typing import Any, List, Dict

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, WebSocket
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.websockets import WebSocketDisconnect
from pydantic import BaseModel

from app.api import deps
from app.services.updates import get_all_data, fetch_and_update_allegro, get_all_data_test
from app.core.bg_task_wrapper import TaskWrapper
from app.schemas.pydantic_models import UpdateConfig, ConfigManager, ConnectionManager, CallbackManager
from app.services.allegro_token import get_token_by_id
from app.loggers import ToLog


router = APIRouter(dependencies=[Depends(deps.get_api_token)])
ws_router = APIRouter()
connection_manager = ConnectionManager()


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

    ToLog.write_access(f"Access to update supplier with request: {await request.json()}")
    bg_tasks.add_task(
        TaskWrapper(task=update_as_task).run_task(
            update_config=update_config
        )
    )
    return JSONResponse({"status": "Update task started"})


@ws_router.websocket("/update/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    ToLog.write_access(f"Access to update by websocket")
    await connection_manager.connect(client_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if validate_input_json(data, client_id):
                connection_manager.set_task_status(client_id)
                await update_under_websocket(
                    UpdateConfig(**data),
                    ConfigManager(
                        manager=connection_manager,
                        client_id=client_id
                    )
                )
            else:
                await connection_manager.send_personal_message(
                    {
                        "status": "error",
                        "message": "Task already running"
                    }, client_id
                )
    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)


def validate_input_json(data: Dict, client_id: str) -> bool:
    stop_event = data.get("stop", None)
    if stop_event:
        connection_manager.stops.get(client_id).set()
    if connection_manager.is_task_active(client_id):
        return False
    else:
        return True


# async def update_under_websocket(update_config: UpdateConfig, config_manager: ConfigManager):
#
#     database = deps.AsyncSessLocal()
#     allegro_token = await get_token_by_id(database, update_config.allegro_token_id)
#     multiplier = update_config.multiplier
#     oferta_ids_to_process = update_config.oferta_ids_to_process
#
#     suppliers_list = update_config.suppliers_to_update if update_config.suppliers_to_update else list(
#         supplier_name.values()
#     )
#     for supplier in suppliers_list:
#         filtered_objects = await get_all_data(supplier, True, multiplier)
#         await fetch_and_update_allegro(
#             database,
#             filtered_objects,
#             allegro_token,
#             oferta_ids_to_process=oferta_ids_to_process,
#             config_manager=config_manager
#         )


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
        # try:
        filtered_objects = await get_all_data(supplier, True, multiplier)
        # except Exception as e:
        #     await callback_manager.send_error_callback_async(f"Error with parsing {supplier} data. Try later.")
        #     ToLog.write_error(f"{e}")
        else:
            await fetch_and_update_allegro(
                database,
                filtered_objects,
                allegro_token,
                oferta_ids_to_process=oferta_ids_to_process,
                callback_manager=callback_manager
            )

    ToLog.write_basic("Update Finished")
    await callback_manager.send_finish_callback_async("Update Finished")





