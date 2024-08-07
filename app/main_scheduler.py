import asyncio

from fastapi import FastAPI
from contextlib import asynccontextmanager
from starlette.middleware.cors import CORSMiddleware

from app.api.v1.scheduler_api import api_router as api_router_v1
from app.services.scheduler_service import scheduler_tasks
from app.core.config import settings
from app.loggers import setup_loggers
from app.context import ctx


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создаем пул соединений Redis
    ctx["semaphore"] = asyncio.Semaphore(5)
    scheduler_tasks.scheduler.start()
    # Инициализируем настройки воркера
    yield
    # Закрываем соединение Redis

setup_loggers()

app = FastAPI(title=settings.PROJECT_NAME,
              lifespan=lifespan,
              openapi_url=f"{settings.API_V1_STR}/openapi.json",
              docs_url=f"{settings.API_V1_STR}/docs")


# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router_v1, prefix=settings.API_V1_STR)

