from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.services.allegro_token import get_tokens_list, get_token_by_name, insert_token, delete_token
from app.schemas.token import TokenOfAllegro
from app.models.database_models import AllegroToken
from app.loggers import ToLog


router = APIRouter(dependencies=[Depends(deps.get_api_token)])
