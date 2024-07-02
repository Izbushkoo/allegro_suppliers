from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.api import deps
from app.schemas.pydantic_models import UpdateConfig
from app.loggers import ToLog


router = APIRouter(dependencies=[Depends(deps.get_api_token)])


@router.post("/add_job")
async def add_async_job():
    ...