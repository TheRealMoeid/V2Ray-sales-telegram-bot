"""Database session management."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import settings


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Alias for backward compatibility
async_session = async_session_maker


async def get_db() -> AsyncSession:
    """Get database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Verify the database is reachable on startup.

    Schema management is now handled entirely by Alembic migrations
    (`alembic upgrade head`), which must be run before this process starts
    (see the Docker entrypoint / README). This function intentionally does
    NOT call `Base.metadata.create_all()` anymore: if a model change is
    ever made without a matching migration, we want the app to fail loudly
    here (or on the first query touching the missing/mismatched column)
    rather than have `create_all()` silently patch the live schema and
    mask the drift, as it did previously.
    """
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def close_db():
    """Close database connection."""
    await engine.dispose()
