from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from rt_collab.core.config import get_settings


settings = get_settings()

engine: AsyncEngine = create_async_engine(settings.database_url, future=True, echo=False)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine, expire_on_commit=False, autoflush=False, autocommit=False
)


@asynccontextmanager
async def get_session() -> AsyncSession:  # type: ignore[override]
    session: AsyncSession = SessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

