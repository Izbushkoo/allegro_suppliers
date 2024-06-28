from typing import Optional

from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: Optional[int] = None


class TokenOfAllegro(BaseModel):
    id_: Optional[str]
    account_name: Optional[str]
    redirect_url: Optional[str]
    client_id: Optional[str]
