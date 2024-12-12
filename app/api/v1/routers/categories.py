import asyncio
import httpx
import json
from typing import Optional, Dict, List
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.services.allegro_token import get_token_by_id
from app.services.modules.APITokenManager import check_token
from app.loggers import ToLog

templates = Jinja2Templates("templates")
router = APIRouter()

BASE_URL = "https://api.allegro.pl"


RATE_LIMIT = 2000  # Количество запросов в минуту
CONCURRENT_REQUESTS = 50  # Максимальное количество одновременных запросов

# Вычисляем задержку между запросами для соблюдения лимита
REQUESTS_PER_SECOND = RATE_LIMIT / 60
DELAY_BETWEEN_REQUESTS = 1 / REQUESTS_PER_SECOND

# Структура для хранения результатов
parent_to_children: Dict[str, List[Dict]] = {}

# Семофор для ограничения количества одновременных запросов
semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)


@router.post("/update-categories")
async def update_categories(database: AsyncSession = Depends(deps.get_db_async)):

    allegro_token = await get_token_by_id(database, "7344ce84-2759-4fb1-b206-cf102cc25694")

    try:
        token = await check_token(database, allegro_token)
    except Exception as err:
        ToLog.write_error(f"Error while check and update token {err}")
        return HTTPException(400, "Error during token check and refresh")
    else:
        access_token = token.access_token

    HEADERS = {
        "Authorization": f"Bearer {access_token}",  # Замените на ваш токен
        "Accept": "application/vnd.allegro.public.v1+json"
    }
    # Запускаем обновление категорий
    new_data = build_category_tree(HEADERS)
    # Сохраняем в файл

    with open("cat_tree.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(new_data, indent=2, ensure_ascii=False))

    return JSONResponse({"status": "updated"})


@router.get("/get")
async def get_tree(request: Request):
    with open("cat_tree.json", "r", encoding="utf-8") as file:
        data = json.loads(file.read())

    return templates.TemplateResponse(
        "tree.html",
        {
            "request": request,
            "data": data
        }
    )


async def get_categories(client: httpx.AsyncClient, headers, parent_id: Optional[str] = None, base_url: str = BASE_URL) -> List[Dict]:
    """
    Асинхронно получает список категорий по заданному parent_id.
    Если parent_id не указан, возвращает главные категории.
    """
    url = f"{base_url}/sale/categories"
    params = {}
    if parent_id:
        params["parent.id"] = parent_id

    async with semaphore:
        await asyncio.sleep(DELAY_BETWEEN_REQUESTS)  # Задержка для соблюдения лимита
        try:
            response = await client.get(url, headers=headers, params=params, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            return data.get("categories", [])
        except httpx.HTTPError as e:
            print(f"Ошибка при получении категорий для parent_id={parent_id}: {e}")
            return []

async def fetch_children(client: httpx.AsyncClient, headers, parent_id: Optional[str] = None):
    """
    Асинхронно получает и обрабатывает дочерние категории для заданного parent_id.
    """
    children = await get_categories(client, headers, parent_id=parent_id)
    parent_key = parent_id if parent_id else ""
    parent_to_children[parent_key] = []

    tasks = []
    for cat in children:
        category_info = {
            "id": cat["id"],
            "name": cat["name"],
            "leaf": cat["leaf"]
        }
        parent_to_children[parent_key].append(category_info)
        print(cat["name"])

        # Если категория не листовая, рекурсивно загружаем её детей
        if not cat["leaf"]:
            tasks.append(fetch_children(client, headers, parent_id=cat["id"]))

    # Запускаем все задачи одновременно
    if tasks:
        await asyncio.gather(*tasks)

async def build_category_tree(headers) -> Dict[str, List[Dict]]:
    """
    Асинхронно обходит дерево категорий Allegro, начиная с корневых.
    Возвращает словарь вида:
    {
      "": [ { "id": ..., "name": ..., "leaf": bool }, ... ],
      "some_id": [ { "id": ..., "name": ..., "leaf": bool }, ... ],
      ...
    }
    """
    async with httpx.AsyncClient() as client:
        await fetch_children(client, headers, parent_id=None)

    # Сохраняем результат в файл
    with open("cat_tree.json", "w", encoding="utf-8") as file:
        file.write(json.dumps(parent_to_children, indent=2, ensure_ascii=False))

    return parent_to_children


