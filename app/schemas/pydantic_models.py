import asyncio
from typing import Optional, List, Dict, Literal

from pydantic import BaseModel, Field, ConfigDict, HttpUrl
from fastapi import WebSocket
import httpx
import requests

from app.loggers import ToLog


class CallbackResponse(BaseModel):
    resource_id: Optional[str | None] = Field(default=None)
    status: str
    message: str


class UpdateConfig(BaseModel):

    multiplier: Optional[int | float] = Field(default=1)
    suppliers_to_update: Optional[List[str] | None] = Field(default=None)
    oferta_ids_to_process: Optional[List[str] | None] = Field(default=None)
    callback_url: Optional[str | None] = Field(default=None)
    resource_id: Optional[str | None] = Field(default=None)
    allegro_token_id: str


class ConfigManager(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )
    client_id: str
    manager: ["ConnectionManager"]


class InitializeAuth(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )
    user_id: str
    client_id: str
    client_secret: str
    account_name: str
    account_description: Optional[str | None] = Field(default=None)
    callback_url: Optional[str | None] = Field(default=None)


class OffersRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True
    )
    name: str
    token_id: str = Field(exclude=True)
    publication_status: Optional[str] = Field(default="ACTIVE", alias="publication.status")
    limit: int = Field(default=500)
    offset: int = Field(default=0)


class UpdateOffersRequest(BaseModel):
    token_id: str
    oferta_ids: List[str]
    resource_id: Optional[str] = Field(default=None)
    callback_url: Optional[str] = Field(default=None)
    action: Optional[str] = Field(default="ACTIVATE")


class ConnectionManager(BaseModel):

    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )
    active_connections: Dict[str, WebSocket] = Field(default_factory=dict)
    stops: Dict[str, asyncio.Event] = Field(default_factory=dict)
    task_status: Dict[str, str] = Field(default_factory=dict)

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


class CallbackManager(BaseModel):

    url: Optional[str | None] = Field(default=None)
    resource_id: Optional[str | None] = Field(default=None)

    def create_message(self, message: str, status: Literal["OK", "error", "finished"] = "OK"):
        return CallbackResponse(
            status=status,
            message=message,
            resource_id=self.resource_id
        ).model_dump_json(exclude_none=True)

    async def send_ok_callback_async(self, message: str):
        if self.url:
            try:
                async with httpx.AsyncClient() as client:
                    result = await client.post(self.url, json=self.create_message(message, "OK"))
                    # ToLog.write_basic(f'{result.json} {result.status_code}')
            except Exception:
                pass

    async def send_error_callback_async(self, message: str):
        if self.url:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(self.url, json=self.create_message(message, "error"))
            except Exception:
                pass

    async def send_finish_callback_async(self, message: str):

        if self.url:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(self.url, json=self.create_message(message, "finished"))
            except Exception:
                pass

    def send_ok_callback(self, message: str):
        if self.url:
            try:
                requests.post(self.url, json=self.create_message(message, "OK"))
            except Exception:
                pass

    def send_error_callback(self, message: str):
        if self.url:
            try:
                requests.post(self.url, json=self.create_message(message, "error"))
            except Exception:
                pass

    def send_finish_callback(self, message: str):
        if self.url:
            try:
                requests.post(self.url, json=self.create_message(message, "finished"))
            except Exception:
                pass
