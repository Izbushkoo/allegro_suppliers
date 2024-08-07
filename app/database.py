from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import Session
from sqlmodel.ext.asyncio.session import AsyncSession as AS
import aioredis

from app.core.config import settings


as_engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI_ASYNC.unicode_string())
AsyncSessLocal = async_sessionmaker(bind=as_engine, autoflush=False, expire_on_commit=False, class_=AS)

engine = create_engine(settings.SQLALCHEMY_DATABASE_URI.unicode_string(), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)

redis_pool = aioredis.ConnectionPool(max_connections=30).from_url("redis://redis_suppliers:6379")
redis = aioredis.StrictRedis(connection_pool=redis_pool)



