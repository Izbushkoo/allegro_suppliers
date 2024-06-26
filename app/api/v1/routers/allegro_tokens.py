from typing import List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.services.allegro_token import get_tokens_list, get_token_by_name, insert_token, delete_token, get_token_by_id
from app.schemas.token import TokenOfAllegro
from app.models.database_models import AllegroToken
from app.loggers import ToLog


router = APIRouter(dependencies=[Depends(deps.get_api_token)])


@router.get("/list", response_model=List[TokenOfAllegro])
async def get_tokens(user_id: str, database: AsyncSession = Depends(deps.get_db_async)):

    ToLog.write_access(f"Access to allegro tokens list")
    tokens = await get_tokens_list(database, user_id)
    return [TokenOfAllegro(**token.model_dump(exclude_none=True)) for token in tokens]


@router.post("/add")
async def add_account(account_data: AllegroToken, database: AsyncSession = Depends(deps.get_db_async)):

    ToLog.write_access(f"Access to allegro tokens add")
    written_token = await insert_token(database, account_data)

    return TokenOfAllegro(**written_token.model_dump(exclude_none=True))


@router.get("/get_by_id")
async def add_account(token_id: str, database: AsyncSession = Depends(deps.get_db_async)):

    ToLog.write_access(f"Access to allegro token get by ID")
    return await get_token_by_id(database, token_id)


@router.delete("/delete")
async def delete_account(token_id: str, database: AsyncSession = Depends(deps.get_db_async)):

    ToLog.write_access(f"Access to allegro tokens add")
    deleted_token = await delete_token(database, token_id)

    return TokenOfAllegro(**deleted_token.model_dump(exclude_none=True))










