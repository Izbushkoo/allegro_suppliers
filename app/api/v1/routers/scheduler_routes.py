from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from app.api import deps
from app.schemas.pydantic_models import UpdateConfig
from app.loggers import ToLog


router = APIRouter(dependencies=[Depends(deps.get_api_token)])


@router.post('/task_start')
async def activate_task(update_config: UpdateConfig):
    ...


@router.post("/task_stop")
async def deactivate_task(update_config: UpdateConfig):
    ...