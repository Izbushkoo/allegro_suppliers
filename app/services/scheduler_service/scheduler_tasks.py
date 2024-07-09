import asyncio
import base64
import datetime
import json
import re

from fastapi.exceptions import HTTPException
import redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.events import EVENT_JOB_ERROR

from app.api import deps
from app.utils import serialize_data, deserialize_data, EscapedManager
from app.api.v1.routers.allegro_offerta_update import update_as_task_in_bulks
from app.services.updates import get_all_data, fetch_and_update_allegro, fetch_data_from_db_sync, \
    fetch_and_update_allegro_sync, get_all_data_sync
from app.schemas.pydantic_models import UpdateConfig
from app.services.allegro_token import get_token_by_id, get_token_by_id_sync
from app.loggers import ToLog

redis_client = redis.StrictRedis(host="redis_suppliers", port=6379, db=0)


jobstores = {
    "default": RedisJobStore(host="redis_suppliers", port=6379, db=0)
}

# executors = {
#     "default": ProcessPoolExecutor(20)
# }

job_defaults = {
    'max_instances': 1
}

scheduler = AsyncIOScheduler(jobstores=jobstores, job_defaults=job_defaults)

supplier_config = {
    "pgn": "9,21",
    "unimet": "10,22",
    "hurtprem": "11,23",
    "rekman": "12,0",
    "growbox": "13,1"
}


def job_error_listener(event):
    job = scheduler.get_job(event.job_id)
    if job:
        ToLog.write_error(f"Job {event.job_id} failed. Retrying with the same parameters...")
        # Повторный запуск задачи с теми же параметрами
        scheduler.add_job(
            job.func,
            trigger="date",
            run_date=datetime.datetime.now() + datetime.timedelta(seconds=5),
            args=job.args,
            kwargs=job.kwargs
        )


async def add_tasks_as_one(user_id: str, routine: str, update_config: UpdateConfig, **kwargs):

    semaphore = kwargs.get("semaphore")

    suppliers_list = update_config.suppliers_to_update if update_config.suppliers_to_update else list(
        supplier_config.keys()
    )
    ToLog.write_basic(f"{suppliers_list}")
    ofertas = update_config.oferta_ids_to_process

    if not ofertas:
        ofertas = []

    database = deps.AsyncSessLocal()
    allegro_token = await get_token_by_id(database, update_config.allegro_token_id)

    oferta_ids_serialized = serialize_data(ofertas)
    tasks = []
    task_id = "_".join(suppliers_list) + f"__{user_id}__{update_config.allegro_token_id}"

    all_jobs = scheduler.get_jobs()
    for job in all_jobs:
        if job.id.split("__")[2] == update_config.allegro_token_id:
            raise HTTPException(status_code=400, detail="Given account already used in another Job.")

    try:
        if routine == "4_hours":
            scheduler.add_job(
                update_as_task_in_bulks, trigger="cron", id=task_id,
                replace_existing=True,
                kwargs={"update_config": update_config, "semaphore": semaphore},
                hour="*/4",
                # minute="*/1"
            )
        else:
            hour, minute = routine.split(":")
            scheduler.add_job(
                update_as_task_in_bulks, trigger="cron", id=task_id,
                replace_existing=True,
                kwargs={"update_config": update_config, "semaphore": semaphore},
                hour=hour,
                minute=minute
            )
    except Exception as err:
        ToLog.write_error(f"{err}")
    else:
        redis_client.set(task_id, oferta_ids_serialized)
        await EscapedManager.add_to_escaped(allegro_token.access_token, ofertas)

        database = deps.AsyncSessLocal()
        allegro_token = await get_token_by_id(database, update_config.allegro_token_id)

        to_append = {
            "suppliers": suppliers_list,
            "allegro_account": {
                "name": allegro_token.account_name,
                "token_id": allegro_token.id_
            },
            "routine": routine,
            "ofertas": ofertas
        }

        tasks.append(to_append)

    return tasks


async def stop_task(user_id: str, update_config: UpdateConfig):

    suppliers_list = update_config.suppliers_to_update if update_config.suppliers_to_update else list(
        supplier_config.keys()
    )

    database = deps.AsyncSessLocal()
    allegro_token = await get_token_by_id(database, update_config.allegro_token_id)

    ToLog.write_basic(f"{suppliers_list}")
    try:
        task_id = "_".join(suppliers_list) + f"__{user_id}__{update_config.allegro_token_id}"
        if scheduler.get_job(task_id):
            scheduler.remove_job(task_id)
            this_ofertas_serialized = redis_client.get(task_id)
            this_ofertas_deserialized = deserialize_data(this_ofertas_serialized)
            await EscapedManager.remove_form_escaped(allegro_token.access_token, this_ofertas_deserialized)
            redis_client.delete(task_id)
    except Exception:
        raise


async def update_supplier(supplier, update_config: UpdateConfig):

    database = deps.AsyncSessLocal()
    allegro_token = await get_token_by_id(database, update_config.allegro_token_id)
    multiplier = update_config.multiplier
    oferta_ids_to_process = update_config.oferta_ids_to_process

    filtered_objects = await get_all_data(supplier, True, multiplier)
    await fetch_and_update_allegro(
        database,
        filtered_objects,
        allegro_token,
        oferta_ids_to_process=oferta_ids_to_process,
    )

    ToLog.write_basic("Update Finished")


def update_supplier_sync(supplier, update_config: UpdateConfig):

    database = deps.SessionLocal()
    allegro_token = get_token_by_id_sync(database, update_config.allegro_token_id)
    multiplier = update_config.multiplier
    oferta_ids_to_process = update_config.oferta_ids_to_process

    filtered_objects = get_all_data_sync(supplier, True, multiplier)
    fetch_and_update_allegro_sync(
        database,
        filtered_objects,
        allegro_token,
        oferta_ids_to_process=oferta_ids_to_process,
    )

    ToLog.write_basic("Update Finished")


def update_suppliers_sync(suppliers_list, update_config: UpdateConfig):
    database = deps.SessionLocal()
    allegro_token = get_token_by_id_sync(database, update_config.allegro_token_id)
    multiplier = update_config.multiplier
    oferta_ids_to_process = update_config.oferta_ids_to_process

    for supplier in suppliers_list:
        filtered_objects = get_all_data_sync(supplier, True, multiplier)
        fetch_and_update_allegro_sync(
            database,
            filtered_objects,
            allegro_token,
            oferta_ids_to_process=oferta_ids_to_process,
        )

    ToLog.write_basic("Update Finished")


async def get_single_job(job_id: str):

    job = scheduler.get_job(job_id)
    job_identifiers = job_id.split("__")

    database = deps.AsyncSessLocal()
    allegro_token = await get_token_by_id(database, job_identifiers[2])

    to_return = {
        "suppliers": job_identifiers[0].split("_"),
        "allegro_account": {
            "name": allegro_token.account_name,
            "token_id": allegro_token.id_
        },
        "routine": define_trigger(job.trigger),
        "ofertas": deserialize_data(redis_client.get(job.id))
    }
    return to_return


async def job_list(user_id: str):
    database = deps.AsyncSessLocal()
    # ToLog.write_basic(f"{allegro_token}")
    jobs = scheduler.get_jobs()

    active_jobs = []
    for job in jobs:
        job_identifiers = job.id.split("__")
        if job_identifiers[1] == user_id:
            allegro_token = await get_token_by_id(database, job_identifiers[2])
            trigger = f"{scheduler.get_job(job.id).trigger}"
            ToLog.write_basic(trigger)
            active_jobs.append({
                "suppliers": job_identifiers[0].split("_"),
                "allegro_account": {
                    "name": allegro_token.account_name,
                    "token_id": allegro_token.id_
                },
                "routine": define_trigger(trigger),
                "ofertas": deserialize_data(redis_client.get(job.id))
            })
    return active_jobs


async def job_list_with_acc(user_id: str, account_id: str):
    database = deps.AsyncSessLocal()
    # ToLog.write_basic(f"{allegro_token}")
    jobs = scheduler.get_jobs()

    active_jobs = []
    for job in jobs:
        job_identifiers = job.id.split("__")
        if job_identifiers[1] == user_id and job_identifiers[2] == account_id:
            allegro_token = await get_token_by_id(database, job_identifiers[2])
            trigger = f"{scheduler.get_job(job.id).trigger}"
            ToLog.write_basic(trigger)
            active_jobs.append({
                "suppliers": job_identifiers[0].split("_"),
                "allegro_account": {
                    "name": allegro_token.account_name,
                    "token_id": allegro_token.id_
                },
                "routine": define_trigger(trigger),
                "ofertas": deserialize_data(redis_client.get(job.id))
            })
    return active_jobs


def define_trigger(trigger_string: str):
    if "hour='*/4'" in trigger_string or "minute='*/1'" in trigger_string:
        return "4_hours"
    else:
        pattern = r"hour='(\d+)', minute='(\d+)'"
        match = re.search(pattern, trigger_string)

        hours = match.group(1)
        minutes = match.group(2)
        return f"{hours}:{minutes}"




scheduler.add_listener(job_error_listener, EVENT_JOB_ERROR)

