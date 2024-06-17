import uuid
from typing import Optional

from sqlmodel import Field, SQLModel


def uuid_as_string():
    return str(uuid.uuid4())


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str
    email: str
    password: str
    is_active: bool = True


class AllegroToken(SQLModel, table=True):
    __tablename__ = "allegro_tokens"

    id_: Optional[str] = Field(primary_key=True, default_factory=uuid_as_string)
    belongs_to: str = Field(nullable=False)
    account_name: Optional[str] = Field(default=None, nullable=True)
    description: Optional[str] = Field(default=None, nullable=True)
    access_token: str
    refresh_token: str
    client_id: str
    client_secret: str
    redirect_url: str
