from typing import List

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, and_

from app.models import database_models as token


async def get_tokens_list(database: AsyncSession, user_id: str):

    async with database as session:
        statement = select(token.AllegroToken).where(token.AllegroToken.belongs_to == user_id)
        result = await session.exec(statement)
        return result.all()


async def get_token_by_id(database: AsyncSession, token_id: str) -> token.AllegroToken | List:

    async with database as session:
        statement = select(token.AllegroToken).where(
            token.AllegroToken.id_ == token_id
        )
        result = await session.exec(statement)
        return result.first() if result else []


async def get_token_by_name(database: AsyncSession, token_name: str):
    async with database as session:
        statement = select(token.AllegroToken).where(token.AllegroToken.account_name == token_name)
        result = await session.exec(statement)
        return result.first() if result else []


async def update_token_by_id(database: AsyncSession, token_id: str, access_token: str, refresh_token: str
                             ) -> token.AllegroToken:
    async with database as session:
        statement = select(token.AllegroToken).where(token.AllegroToken.id_ == token_id)
        result = await session.exec(statement)
        current_token = result.first()
        current_token.access_token = access_token
        current_token.refresh_token = refresh_token
        session.add(current_token)
        await session.commit()
        await session.refresh(current_token)
        return current_token


async def insert_token(database: AsyncSession, token_: token.AllegroToken):
    async with database as session:
        session.add(token_)
        await session.commit()
        await session.refresh(token_)
        return token_


async def delete_token(database: AsyncSession, token_id: str):
    async with database as session:
        statement = select(token.AllegroToken).where(token.AllegroToken.id_ == token_id)
        result = await session.exec(statement)
        token_to_delete = result.first()
        await session.delete(token_to_delete)
        await session.commit()
        return token_to_delete











