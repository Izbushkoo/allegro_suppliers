from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api import deps
from app.schemas.pydantic_models import UpdateConfig
from app.services.scheduler_service.scheduler_tasks import stop_task, job_list, add_tasks_as_one, get_single_job, \
    job_list_with_acc
from app.loggers import ToLog


router = APIRouter(dependencies=[Depends(deps.get_api_token)])
# router = APIRouter()


@router.post('/task_start')
async def activate_task(user_id: str, routine: str, update_config: UpdateConfig):
    ToLog.write_access(f"Access to task start")
    result = await add_tasks_as_one(user_id, routine, update_config)
    return result


@router.post("/task_stop")
async def deactivate_task(user_id: str, update_config: UpdateConfig):
    ToLog.write_access(f"Access to task stop")
    try:
        stop_task(user_id, update_config)
    except Exception:
        return JSONResponse({"status": "error", "message": "task(s) stopped"})
    else:
        return JSONResponse({"status": "OK", "message": "task(s) stopped"})


@router.get("/list_tasks")
async def get_jobs_list(user_id: str):
    ToLog.write_access(f"Access to task list")
    jobs = await job_list(user_id)
    return jobs


@router.get("/list_tasks_by_acc")
async def get_jobs_list(user_id: str, account_id):
    ToLog.write_access(f"Access to task list with acc")
    jobs = await job_list_with_acc(user_id, account_id)
    return jobs


@router.get("/get_task")
async def get_jobs_list(job_id: str):
    jobs = get_single_job(job_id)
    return jobs

