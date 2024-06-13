from typing import List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.services.allegro_token import get_tokens_list, get_token_by_name
from app.schemas.token import TokenOfAllegro


router = APIRouter()


@router.get("/list", response_model=List[TokenOfAllegro])
async def get_tokens(database: AsyncSession = Depends(deps.get_db_async)):
    tokens = await get_tokens_list(database)
    return [TokenOfAllegro(**token.model_dump(exclude_none=True)) for token in tokens]
