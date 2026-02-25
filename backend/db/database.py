from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from ..core.config import settings
from ..core.logging_config import get_logger
from .models import Base

logger = get_logger(__name__)

engine: Optional[AsyncEngine] = None
async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    global engine
    if engine is None:
        database_url = settings.DATABASE_URL
        
        if database_url.startswith("sqlite"):
            engine = create_async_engine(
                database_url,
                echo=settings.DATABASE_ECHO,
                poolclass=NullPool,
            )
        elif database_url.startswith("postgresql+asyncpg"):
            engine = create_async_engine(
                database_url,
                echo=settings.DATABASE_ECHO,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                poolclass=QueuePool,
            )
        else:
            engine = create_async_engine(
                database_url,
                echo=settings.DATABASE_ECHO,
            )
        
        logger.info(
            "Database engine created",
            extra={
                "url_scheme": database_url.split(":")[0] if database_url else "none",
                "pool_size": settings.DATABASE_POOL_SIZE if "postgresql" in database_url else "none",
            },
        )
    
    return engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global async_session_factory
    if async_session_factory is None:
        async_session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return async_session_factory


async def init_db() -> None:
    eng = get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialized")


async def close_db() -> None:
    global engine, async_session_factory
    
    if engine:
        await engine.dispose()
        engine = None
        async_session_factory = None
        logger.info("Database connections closed")


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
