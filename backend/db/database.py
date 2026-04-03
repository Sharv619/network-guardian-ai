from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

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

engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


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
                "pool_size": settings.DATABASE_POOL_SIZE
                if "postgresql" in database_url
                else "none",
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


async def _migrate_existing_tables(engine) -> None:
    """Add missing columns to existing tables (SQLite doesn't support ALTER COLUMN)."""
    import sqlite3

    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "").replace("./", "")
    if not db_path or db_path == settings.DATABASE_URL:
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check and add tenant_id to domains table
        cursor.execute("PRAGMA table_info(domains)")
        domain_cols = [col[1] for col in cursor.fetchall()]
        if "tenant_id" not in domain_cols:
            cursor.execute("ALTER TABLE domains ADD COLUMN tenant_id INTEGER NOT NULL DEFAULT 1")
            logger.info("Migration: Added tenant_id to domains table")

        # Check and add tenant_id to metadata table
        cursor.execute("PRAGMA table_info(metadata)")
        meta_cols = [col[1] for col in cursor.fetchall()]
        if "tenant_id" not in meta_cols:
            cursor.execute("ALTER TABLE metadata ADD COLUMN tenant_id INTEGER NOT NULL DEFAULT 1")
            logger.info("Migration: Added tenant_id to metadata table")

        # Check and add tenant_id to features table
        cursor.execute("PRAGMA table_info(features)")
        feat_cols = [col[1] for col in cursor.fetchall()]
        if "tenant_id" not in feat_cols:
            cursor.execute("ALTER TABLE features ADD COLUMN tenant_id INTEGER NOT NULL DEFAULT 1")
            logger.info("Migration: Added tenant_id to features table")

        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Schema migration skipped or failed: {e}")


async def init_db() -> None:
    eng = get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Run schema migration for existing tables
    await _migrate_existing_tables(eng)

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
