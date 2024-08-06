from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.services.allegro_token import get_token_by_id
from app.services.modules.APITokenManager import check_token
from app.api import deps
from app.schemas.pydantic_models import UpdateConfig
from app.services.scheduler_service.scheduler_tasks import stop_task, job_list, add_tasks_as_one, get_single_job, \
    job_list_with_acc, add_synchro_products_job
from app.loggers import ToLog
from app.schemas.pydantic_models import SynchronizeOffersRequest, CallbackManager
from app.services.updates import get_all_supplier_products_data


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
        await stop_task(user_id, update_config)
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


@router.get("/synchro")
async def syncro_run(
    synchro_request: SynchronizeOffersRequest,
    database: AsyncSession = Depends(deps.get_db_async),
    ):

    callback_manager = CallbackManager(
        url=synchro_request.callback_url,
        resource_id=synchro_request.resource_id
    )

    products = await get_all_supplier_products_data(synchro_request.supplier, callback_manager=callback_manager,
                                                    multiplier=synchro_request.multiplier)

    allegro_token = await get_token_by_id(database, synchro_request.token_id)

    try:
        await callback_manager.send_ok_callback_async(
            f"Проверяем валидность токена '{allegro_token.account_name}'..."
        )
        token = await check_token(database, allegro_token, callback_manager)
    except Exception as err:
        ToLog.write_error(f"Error while check and update token {err}")
        await callback_manager.send_error_callback(f"Ошибка во время проверки и обновления токена: {err}")
        raise HTTPException(status_code=403, detail="Invalid token")
    else:
        access_token = token.access_token

        job = add_synchro_products_job(
            synchro_config=synchro_request,
            access_token=access_token,
            products=products
        )

    return JSONResponse({"status": "OK", "message": "Synchronization started", "job_id": job.id})



