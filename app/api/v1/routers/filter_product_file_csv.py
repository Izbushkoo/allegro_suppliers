import asyncio
import copy
import csv
import io
from typing import List, Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.responses import StreamingResponse, JSONResponse
import httpx

from app.api import deps
from app.core.bg_task_wrapper import TaskWrapper
from app.loggers import ToLog
from app.services.allegro_token import get_tokens_list, get_token_by_id
from app.services.modules.APITokenManager import check_token
from app.services.updates import get_all_supplier_products_data
from app.schemas.pydantic_models import CallbackManager, SynchronizeOffersRequest

# router = APIRouter(dependencies=[Depends(deps.get_api_token)])
router = APIRouter()


@router.get("/get_all_skus")
async def get_all_skus(
        supplier_prefix: str,
        database: AsyncSession = Depends(deps.get_db_async),
        user_id: str = "local"):

    try:
        tokens = await get_tokens_list(database, user_id=user_id)
    except Exception as err:
        raise HTTPException(500, detail=f"some error {err}")
    else:
        if tokens:
            access_token = tokens[0].access_token
            try:
                await check_token(database, tokens[0])
            except Exception:
                raise HTTPException(500, detail="Error with token checking")
        else:
            raise HTTPException(404, detail="Token list is empty")

    all_skus = await get_all_offers_filter_skus(access_token, supplier_prefix)
    return [lambda x: x.replace(f"{supplier_prefix}_", '') for x in all_skus]


@router.post("/filter_and_prefix")
async def refactor(supplier_prefix: str, request: Request, file: UploadFile,
                   database: AsyncSession = Depends(deps.get_db_async), user_id: str = "local"):
    """Данный роут принимает на вход csv-файл с продуктами baselinker, фильтрует его на основании уже имеющихся
    на allegro аккаунте офферт по номеру sku и префиксу, в итоговом столбце sku получает также указанный префикс,
    преобразует его в формат пригодный для импорта в BaseLinker."""
    # ToLog.write_basic(f"{request.headers}")
    if file.content_type == "text/csv":

        data = await file.read()
        await file.close()
        ToLog.write_basic("File received...Processing.")
        input_stream = io.StringIO(data.decode("utf-8-sig"))
        try:
            # Чтение CSV файла в любом формате
            reader = csv.DictReader(input_stream, delimiter=";")
        except csv.Error as err:
            raise HTTPException(422, f"bad file content {err}")
        else:
            data_list: List[Any] = [row for row in reader]
            ToLog.write_basic(f"Data list length {len(data_list)}")

        try:
            tokens = await get_tokens_list(database, user_id=user_id)
        except Exception as err:
            raise HTTPException(500, detail=f"some error {err}")
        else:
            if tokens:
                access_token = tokens[0].access_token
                try:
                    await check_token(database, tokens[0])
                except Exception:
                    raise HTTPException(500, detail="Error with token checking")
            else:
                raise HTTPException(404, detail="Token list is empty")

        all_skus = await get_all_offers_filter_skus(access_token, supplier_prefix)
        ToLog.write_basic(f"all skus length {len(all_skus)}")

        filtered_data_for_file = []
        for item in data_list:
            if f"{supplier_prefix}_FS_{item['product_sku']}" not in all_skus:
                new_item = copy.deepcopy(item)
                new_item["product_sku"] = f"{supplier_prefix}_FS_{item['product_sku']}"
                filtered_data_for_file.append(new_item)
        ToLog.write_basic(f"filtered data length {len(filtered_data_for_file)}")

        # Преобразование данных обратно в CSV формат
        output_stream = io.StringIO()
        fieldnames = reader.fieldnames
        writer = csv.DictWriter(output_stream, fieldnames=fieldnames, delimiter=";", quoting=csv.QUOTE_MINIMAL,
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(filtered_data_for_file)

        # Перемещение указателя в начало буфера
        output_stream.seek(0)

        # Подготовка ответа с преобразованным CSV файлом
        response = StreamingResponse(output_stream, media_type="application/octet-stream")
        response.headers["Content-Disposition"] = f"attachment; filename=Prepared_{file.filename}"
        return response
    else:
        ToLog.write_error("File is not of CSV format")
        return HTTPException(status_code=422, detail="File is not of csv format.")


async def get_offers(access_token: str, limit=1000, offset=0):

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/vnd.allegro.public.v1+json",
        "Accept": "application/vnd.allegro.public.v1+json",
    }
    params = {
        "limit": limit,
        "offset": offset
    }

    url = f"https://api.allegro.pl/sale/offers"

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        resp = response.json()

    return resp


async def get_all_offers_filter_skus(access_token: str, supplier_prefix: str) -> List[str]:

    current = 0
    batch = 1000
    total_response = await get_offers(access_token, limit=1)
    total = total_response["totalCount"]
    offers = []
    while current < total:
        batch_offers = await get_offers(access_token, limit=batch, offset=current)
        filtered = []
        for offer in batch_offers["offers"]:
            if offer["external"]:
                if offer["external"]['id'] and offer["external"]['id'].startswith(supplier_prefix):
                    filtered.append(offer)
            else:
                ToLog.write_basic(offer.get("id"))

        offers += filtered
        current += batch_offers["count"]

    all_skus = []
    for item in offers:
        if item["external"]:
            all_skus.append(item["external"]["id"])

    return all_skus


async def get_all_offers_filter(access_token: str, supplier_prefix: str) -> List[str]:

    current = 0
    batch = 1000
    total_response = await get_offers(access_token, limit=1)
    total = total_response["totalCount"]
    offers = []
    while current < total:
        batch_offers = await get_offers(access_token, limit=batch, offset=current)
        filtered = []
        for offer in batch_offers["offers"]:
            if offer["external"]:
                if offer["external"]['id'] and offer["external"]['id'].startswith(supplier_prefix):
                    filtered.append(offer)
            else:
                ToLog.write_basic(offer.get("id"))

        offers += filtered
        current += batch_offers["count"]

    return offers











