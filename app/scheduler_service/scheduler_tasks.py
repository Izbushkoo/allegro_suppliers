from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from app.api import deps
from app.services.updates import get_all_data, fetch_and_update_allegro, get_all_data_test
from app.database import as_engine
from app.core.bg_task_wrapper import TaskWrapper
from app.schemas.pydantic_models import UpdateConfig, ConfigManager, ConnectionManager, CallbackManager
from app.services.allegro_token import get_token_by_id
from app.loggers import ToLog
from app.core.config import settings


jobstores = {
    "default": SQLAlchemyJobStore(engine=as_engine)
}

scheduler = AsyncIOScheduler(jobstores=jobstores)

supplier_config = {
    "pgn": "9,21",
    "unimet": "10,22",
    "hurtprem": "11,23",
    "rekman": "12,0",
    "growbox": "13,1"
}


async def add_task(update_config: UpdateConfig):

    suppliers_list = update_config.suppliers_to_update if update_config.suppliers_to_update else list(
        supplier_config.keys()
    )
    ToLog.write_basic(f"{suppliers_list}")
    for supplier in suppliers_list:
        if not scheduler.get_job(supplier):
            scheduler.add_job(
                update_supplier, trigger="cron", id=supplier, replace_existing=True,
                kwargs={"supplier": supplier, "update_config": update_config},
                # hours=supplier_config[supplier],
                minutes="*/10"
            )


def stop_task(update_config: UpdateConfig):

    suppliers_list = update_config.suppliers_to_update if update_config.suppliers_to_update else list(
        supplier_config.keys()
    )
    ToLog.write_basic(f"{suppliers_list}")
    for supplier in suppliers_list:
        if scheduler.get_job(supplier):
            scheduler.remove_job(supplier)


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
