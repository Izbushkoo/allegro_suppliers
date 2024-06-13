from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.services.updates import get_all_data, fetch_and_update_allegro
from app.core.bg_task_wrapper import TaskWrapper
from app.schemas.pydantic_models import UpdateConfig
from app.services.allegro_token import get_token_by_id


router = APIRouter()

supplier_name = {
    "pgn": "pgn",
    "unimet": "unimet",
    "hurtprem": "hurtprem",
    "rekman": "rekman",
    "growbox": "growbox"
}


@router.post("/update")
async def update_all_suppliers(update_config: UpdateConfig, bg_tasks: BackgroundTasks):
    """Обновить Аллегро оферты для заданного аккаунта."""
    bg_tasks.add_task(
        TaskWrapper(task=update_as_task).run_task(
            update_config=update_config
        )
    )
    return {"status": "Update task started"}


async def update_as_task(update_config: UpdateConfig):

    database = deps.AsyncSessLocal()
    allegro_token = await get_token_by_id(database, update_config.allegro_token_id)
    multiplier = update_config.multiplier
    oferta_ids_to_process = update_config.oferta_ids_to_process

    suppliers_list = update_config.suppliers_to_update if update_config.suppliers_to_update else list(
        supplier_name.values()
    )

    for supplier in suppliers_list:
        filtered_objects = await get_all_data(supplier, True, multiplier)
        await fetch_and_update_allegro(
            database,
            filtered_objects,
            allegro_token,
            oferta_ids_to_process=oferta_ids_to_process
        )




