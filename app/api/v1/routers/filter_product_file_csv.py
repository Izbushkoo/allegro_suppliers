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
from app.services.modules.AlegroApiManager import create_single_offer
from app.services.modules.DatabaseManager import MongoManager
from app.services.configs.AllegroConfig import supplier_settings as allegro_config
from app.services.updates import get_all_supplier_products_data
from app.services.modules.DataFiltering.GetAllData import filter_for_supplier_items
from app.schemas.pydantic_models import CallbackManager, SynchronizeOffersRequest
from app.services.modules.AlegroApiManager import search_product_by_ean_return_first

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


@router.get("/synchronize_offers_with_supplier")
async def synchronize_products_with_supplier(
        synchro_request: SynchronizeOffersRequest,
        bg_tasks: BackgroundTasks,
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

    bg_tasks.add_task(
        TaskWrapper(task=process_complete_synchro_task).run_task(
            synchro_config=synchro_request,
            access_token=access_token,
            products=products
        )
    )
    return JSONResponse({"status": "OK", "message": "Synchronization started"})


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


async def handle_single_product(supplier_product, allegro_access_token):
    ean = supplier_product["ean"]
    found_product = await search_product_by_ean_return_first(ean, allegro_access_token)
    if found_product:
        if supplier_product["stock"] > 0:
            product_to_work_with = {
                **supplier_product,
                "allegro_product_id": found_product["id"],
                "category_id": found_product["category"]["id"],
                "product_name": found_product["name"]
            }
            allegro_response = await create_single_offer(product_to_work_with, access_token=allegro_access_token)
            if allegro_response:
                product_to_work_with["allegro_oferta_id"] = allegro_response["id"]
                product_to_work_with["allegro_we_sell_it"] = True
                return product_to_work_with


async def process_complete_synchro_task(synchro_config: SynchronizeOffersRequest, access_token, products,
                                        batch: int = 200):

    tasks = []
    all_results = []
    for i in range(0, len(products), batch):
        for product in products[i: i + batch]:
            task = asyncio.create_task(handle_single_product(product, access_token))
            tasks.append(task)
        results = await asyncio.gather(*tasks)
        all_results += [result for result in results if result]

    await MongoManager.append_bulks(all_results, synchro_config.supplier)









