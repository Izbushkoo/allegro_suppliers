from fastapi import APIRouter
from app.api.v1.routers.scheduler import scheduler_routes, arq_routes

api_router = APIRouter()


api_router.include_router(scheduler_routes.router, prefix="/scheduler", tags=["Управление Cron job."])
api_router.include_router(arq_routes.router, prefix="/arq", tags=["Управление Ассинхронным Cron job с "
                                                                  "использованием очереди задач"])


