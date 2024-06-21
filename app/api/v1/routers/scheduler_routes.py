from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.api import deps
from app.schemas.pydantic_models import UpdateConfig
from app.scheduler_service.scheduler_tasks import stop_task, add_task
from app.loggers import ToLog


# router = APIRouter(dependencies=[Depends(deps.get_api_token)])
router = APIRouter()


@router.post('/task_start')
async def activate_task(update_config: UpdateConfig):
    add_task(update_config)
    return JSONResponse({"status": "OK", "message": "task(s) started"})


@router.post("/task_stop")
async def deactivate_task(update_config: UpdateConfig):
    stop_task(update_config)
    return JSONResponse({"status": "OK", "message": "task(s) stopped"})
