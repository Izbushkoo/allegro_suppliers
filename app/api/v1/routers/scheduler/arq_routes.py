from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from arq.jobs import Job

from app.api import deps
from app.context import ctx
from app.schemas.pydantic_models import UpdateConfig
from app.loggers import ToLog


router = APIRouter(dependencies=[Depends(deps.get_api_token)])


@router.post("/add_job")
async def add_async_job():
    redis = ctx["redis"]


@router.get("/get_job")
async def get_job(job_id: str):
    redis = ctx["redis"]
    job = Job(
        job_id=job_id,
        redis=redis
    )



