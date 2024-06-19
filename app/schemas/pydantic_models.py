import asyncio
from typing import Optional, List, Dict

from pydantic import BaseModel, Field
from fastapi import WebSocket


class UpdateConfig(BaseModel):

    multiplier: Optional[int | float] = Field(default=1)
    suppliers_to_update: Optional[List[str]] = Field(default=None)
    oferta_ids_to_process: Optional[List[str]] = Field(default=None)
    allegro_token_id: str


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
