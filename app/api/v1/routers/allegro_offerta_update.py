import asyncio
from typing import Any, List, Dict

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, WebSocket
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.websockets import WebSocketDisconnect
from pydantic import BaseModel

from app.api import deps
from app.services.updates import get_all_data, fetch_and_update_allegro
from app.core.bg_task_wrapper import TaskWrapper
from app.schemas.pydantic_models import UpdateConfig
from app.services.allegro_token import get_token_by_id
from app.loggers import ToLog


router = APIRouter(dependencies=[Depends(deps.get_api_token)])

supplier_name = {
    "pgn": "pgn",
    "unimet": "unimet",
    "hurtprem": "hurtprem",
    "rekman": "rekman",
    "growbox": "growbox"
}


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
    return {"status": "Update task started"}


class ConfigManager(BaseModel):
    client_id: str
    manager: ["ConnectionManager"]


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.stops: Dict[str, asyncio.Event] = {}
        self.task_status: Dict[str, str] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id)

    async def send_personal_message(self, message: Dict, client_id: str):
        socket = self.active_connections.get(client_id)
        if socket:
            await socket.send_json(message)
    
    def is_task_active(self, client_id: str) -> bool:
        return self.task_status.get(client_id) == "in progress"

    def set_task_status(self, client_id: str, status: str = "in progress"):
        self.task_status[client_id] = status


connection_manager = ConnectionManager()


@router.websocket("/update/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
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


async def update_under_websocket(update_config: UpdateConfig, config_manager: ConfigManager):

    database = deps.AsyncSessLocal()
    allegro_token = await get_token_by_id(database, update_config.allegro_token_id)
    multiplier = update_config.multiplier
    oferta_ids_to_process = update_config.oferta_ids_to_process

    suppliers_list = update_config.suppliers_to_update if update_config.suppliers_to_update else list(
        supplier_name.values()
    )

    for supplier in suppliers_list:
        filtered_objects = await get_all_data(supplier, True, multiplier)
        await fetch_and_update_allegro(
            database,
            filtered_objects,
            allegro_token,
            oferta_ids_to_process=oferta_ids_to_process,
            config_manager=config_manager
        )


async def update_as_task(update_config: UpdateConfig):

    database = deps.AsyncSessLocal()
    allegro_token = await get_token_by_id(database, update_config.allegro_token_id)
    multiplier = update_config.multiplier
    oferta_ids_to_process = update_config.oferta_ids_to_process

    suppliers_list = update_config.suppliers_to_update if update_config.suppliers_to_update else list(
        supplier_name.values()
    )

    for supplier in suppliers_list:
        filtered_objects = await get_all_data(supplier, True, multiplier)
        await fetch_and_update_allegro(
            database,
            filtered_objects,
            allegro_token,
            oferta_ids_to_process=oferta_ids_to_process
        )




