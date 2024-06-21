from fastapi import APIRouter
from app.api.v1.routers import scheduler_routes

api_router = APIRouter()


api_router.include_router(scheduler_routes.router, prefix="/scheduler", tags=["Управление Cron job."])
