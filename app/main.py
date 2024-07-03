import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from arq.connections import create_pool, RedisSettings
from arq.cron import CronJob

from app.api.v1.api import api_router as api_router_v1
from app.services.scheduler_service.arq_tasks import WorkerSettings
from app.core.config import settings
from app.loggers import setup_loggers
from app.context import ctx


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создаем пул соединений Redis
    redis = await create_pool(RedisSettings(host='redis_suppliers', port=6379))
    # Инициализируем настройки воркера
    ctx["redis"] = redis
    yield
    # Закрываем соединение Redis
    await redis.close()

setup_loggers()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan,
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


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True, port=8787)
