from fastapi import APIRouter

from app.api.v1.routers import auth, users, allegro_offerta_update, allegro_tokens

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["Пользователи"])
api_router.include_router(auth.router, prefix="/auth", tags=["Авторизация"])

api_router.include_router(allegro_tokens.router, prefix="/allegro_tokens", tags=["Аллегро токкены."])

api_router.include_router(allegro_offerta_update.router, prefix="/update", tags=["Обновление оферт Аллегро."])
