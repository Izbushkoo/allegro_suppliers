from typing import List

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import Session
from sqlmodel import select, and_

from app.models import database_models


async def get_all_failed_eans(database: AsyncSession) -> List:

    async with database as session:
        statement = select(database_models.FailedEans)
        result = await session.exec(statement)
        all_results = result.all()
        return [res.id for res in all_results]


async def add_failed_ean(database: AsyncSession, ean):
    async with database as session:
        new = database_models.FailedEans(id=ean)
        session.add(new)
        await session.commit()
