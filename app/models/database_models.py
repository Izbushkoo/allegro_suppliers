from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str
    email: str
    password: str
    is_active: bool = True


class AllegroToken(SQLModel, table=True):
    __tablename__ = "allegro_tokens"

    id_: Optional[int] = Field(primary_key=True, index=True)
    account_name: Optional[str] = Field(default=None, nullable=True)
    description: Optional[str] = Field(default=None, nullable=True)
    access_token: str
    refresh_token: str
    client_id: str
    client_secret: str
    redirect_url: str