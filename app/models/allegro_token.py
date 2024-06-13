from typing import Optional

from sqlmodel import Field, SQLModel


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
    scope: str
