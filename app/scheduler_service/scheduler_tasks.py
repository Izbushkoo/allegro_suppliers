import asyncio
import base64
import datetime
import json
import re

import redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ProcessPoolExecutor
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.events import EVENT_JOB_ERROR

from app.api import deps
from app.services.updates import get_all_data, fetch_and_update_allegro, fetch_data_from_db_sync, \
    fetch_and_update_allegro_sync, get_all_data_sync
from app.schemas.pydantic_models import UpdateConfig
from app.services.allegro_token import get_token_by_id, get_token_by_id_sync
from app.loggers import ToLog

redis_client = redis.StrictRedis(host="redis_suppliers", port=6379, db=0)


jobstores = {
    "default": RedisJobStore(host="redis_suppliers", port=6379, db=0)
}

executors = {
    "default": ProcessPoolExecutor(20)
}

job_defaults = {
    'max_instances': 2
}

scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults)

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


async def add_task(user_id: str, routine: str, update_config: UpdateConfig):

    suppliers_list = update_config.suppliers_to_update if update_config.suppliers_to_update else list(
        supplier_config.keys()
    )
    ToLog.write_basic(f"{suppliers_list}")
    ofertas = update_config.oferta_ids_to_process

    if not ofertas:
        ofertas = []

    oferta_ids_serialized = serialize_data(ofertas)
    tasks = []
    for supplier in suppliers_list:
        task_id = supplier + f"__{user_id}__{update_config.allegro_token_id}"
        redis_client.set(task_id, oferta_ids_serialized)
        if not scheduler.get_job(supplier):
            try:
                if routine == "4_hours":
                    scheduler.add_job(
                        update_supplier_sync, trigger="cron", id=task_id,
                        replace_existing=True,
                        kwargs={"supplier": supplier, "update_config": update_config},
                        # hour="*/4",
                        minute="*/4"
                    )
                else:
                    hour, minute = routine.split(":")
                    scheduler.add_job(
                        update_supplier_sync, trigger="cron", id=task_id,
                        replace_existing=True,
                        kwargs={"supplier": supplier, "update_config": update_config},
                        hour=hour,
                        minute=minute
                    )
            except Exception:
                pass
            else:

                database = deps.AsyncSessLocal()
                allegro_token = await get_token_by_id(database, update_config.allegro_token_id)

                to_append = {
                    "supplier": supplier,
                    "allegro_account": {
                        "name": allegro_token.account_name,
                        "token_id": allegro_token.id_
                    },
                    "routine": routine,
                    "ofertas": ofertas
                }

                tasks.append(to_append)
    return tasks


def stop_task(user_id: str, update_config: UpdateConfig):

    suppliers_list = update_config.suppliers_to_update if update_config.suppliers_to_update else list(
        supplier_config.keys()
    )

    ToLog.write_basic(f"{suppliers_list}")
    try:
        for supplier in suppliers_list:
            task_id = supplier + f"__{user_id}__{update_config.allegro_token_id}"
            if scheduler.get_job(task_id):
                scheduler.remove_job(task_id)
                redis_client.delete(task_id)
    except Exception:
        raise


def stop_task_1(update_config: UpdateConfig):

    suppliers_list = update_config.suppliers_to_update if update_config.suppliers_to_update else list(
        supplier_config.keys()
    )
    ToLog.write_basic(f"{suppliers_list}")
    for supplier in suppliers_list:
        task_id = supplier + f"__{update_config.allegro_token_id}"
        if scheduler.get_job(task_id):
            scheduler.remove_job(task_id)


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


async def get_single_job(job_id: str):

    job = scheduler.get_job(job_id)
    job_identifiers = job_id.split("__")

    database = deps.AsyncSessLocal()
    allegro_token = await get_token_by_id(database, job_identifiers[2])

    to_return = {
        "supplier": job_identifiers[0],
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
                "supplier": job_identifiers[0],
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
                "supplier": job_identifiers[0],
                "allegro_account": {
                    "name": allegro_token.account_name,
                    "token_id": allegro_token.id_
                },
                "routine": define_trigger(trigger),
                "ofertas": deserialize_data(redis_client.get(job.id))
            })
    return active_jobs


def define_trigger(trigger_string: str):
    if "hour='*/4'" in trigger_string or "minute='*/4'" in trigger_string:
        return "4_hours"
    else:
        pattern = r"hour='(\d+)', minute='(\d+)'"
        match = re.search(pattern, trigger_string)

        hours = match.group(1)
        minutes = match.group(2)
        return f"{hours}:{minutes}"


def serialize_data(data):
    # Преобразуем данные в JSON
    json_data = json.dumps(data)
    # Кодируем JSON в Base64
    encoded_data = base64.urlsafe_b64encode(json_data.encode()).decode()
    return encoded_data


def deserialize_data(encoded_data):
    # Декодируем Base64 обратно в JSON
    json_data = base64.urlsafe_b64decode(encoded_data).decode()
    # Преобразуем JSON обратно в данные
    data = json.loads(json_data)
    return data


scheduler.add_listener(job_error_listener, EVENT_JOB_ERROR)

