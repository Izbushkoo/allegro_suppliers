import json
import base64
from typing import List

import jwt

from app.database import redis


def serialize_data(data):
    # Преобразуем данные в JSON
    json_data = json.dumps(data)
    # Кодируем JSON в Base64
    encoded_data = base64.urlsafe_b64encode(json_data.encode()).decode()
    return encoded_data


def deserialize_data(encoded_data):
    # Декодируем Base64 обратно в JSON
    json_data = base64.urlsafe_b64decode(encoded_data).decode()
    # Преобразуем JSON обратно в данные
    data = json.loads(json_data)
    return data


class NotFoundUserError(Exception):
    ...


class EscapedOfertasManager:

    def __init__(self, redis_client=None):
        self._client = redis_client or redis

    @staticmethod
    def decode_token_and_get_user(token: str):
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
        except jwt.exceptions.DecodeError:
            raise
        else:
            user = decoded.get("user_name")
            if user:
                return user
            else:
                raise NotFoundUserError("Token does not contain User")

    async def get_current_escaped(self, token: str, user: str | None = None):
        user = user if user else self.decode_token_and_get_user(token)
        result = await self._client.get(user)
        return deserialize_data(result) if result else []

    async def add_to_escaped(self, token: str, oferta_ids: List[str]):
        user = self.decode_token_and_get_user(token)
        current = await self.get_current_escaped(token, user)
        new_escaped = current + oferta_ids
        await self._client.set(user, serialize_data(new_escaped))

    async def remove_form_escaped(self, token: str, oferta_ids: List[str]):
        user = self.decode_token_and_get_user(token)
        current = await self.get_current_escaped(token, user)
        new_escaped = [item for item in current if item not in oferta_ids]
        await self._client.set(user, serialize_data(new_escaped))


EscapedManager = EscapedOfertasManager()


