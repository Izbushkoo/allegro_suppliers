from typing import List
import json
import base64
from fastapi.exceptions import HTTPException

from arq.connections import ArqRedis
from arq.jobs import JobDef, Job
import redis

from app.context import ctx
from app.api.v1.routers.allegro_offerta_update import update_as_task_in_bulks
from app.schemas.pydantic_models import UpdateConfig
from app.loggers import ToLog

redis_client = redis.StrictRedis(host="redis_suppliers", port=6379, db=0)

supplier_config = {
    "pgn": "9,21",
    "unimet": "10,22",
    "hurtprem": "11,23",
    "rekman": "12,0",
    "growbox": "13,1"
}


async def get_jobs_list():
    redis_: ArqRedis = ctx["redis"]
    jobs: List[JobDef] = await redis_.queued_jobs()
    return jobs


async def add_tasks_as_one(user_id: str, routine: str, update_config: UpdateConfig):

    redis_: ArqRedis = ctx["redis"]
    suppliers_list = update_config.suppliers_to_update if update_config.suppliers_to_update else list(
        supplier_config.keys()
    )
    ToLog.write_basic(f"{suppliers_list}")
    ofertas = update_config.oferta_ids_to_process

    if not ofertas:
        ofertas = []

    oferta_ids_serialized = serialize_data(ofertas)
    tasks = []
    task_id = "_".join(suppliers_list) + f"__{user_id}__{update_config.allegro_token_id}"

    all_jobs = await get_jobs_list()
    for job in all_jobs:
        if job.job_id.split("__")[2] == update_config.allegro_token_id:
            raise HTTPException(status_code=400, detail="Given account already used in another Job.")

    redis_client.set(task_id, oferta_ids_serialized)
    try:
        if routine == "4_hours":
            redis_.enqueue_job()
            scheduler.add_job(
                update_suppliers_sync, trigger="cron", id=task_id,
                replace_existing=True,
                kwargs={"suppliers_list": suppliers_list, "update_config": update_config},
                hour="*/4",
                # minute="*/1"
            )
        else:
            hour, minute = routine.split(":")
            scheduler.add_job(
                update_suppliers_sync, trigger="cron", id=task_id,
                replace_existing=True,
                kwargs={"suppliers_list": suppliers_list, "update_config": update_config},
                hour=hour,
                minute=minute
            )
    except Exception as err:
        ToLog.write_error(f"{err}")
    else:

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