from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Create async engine
engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.APP_DEBUG,
    future=True,
    pool_pre_ping=True,
)

# Create async session factory
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

# Create declarative base for models
Base = declarative_base()

# Dependency to get DB session
async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Initialize database
async def init_db():
    # Create all tables that don't exist yet
    # In production, use Alembic migrations
    if settings.APP_ENV == "development" or settings.APP_ENV == "testing":
        async with engine.begin() as conn:
            # await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)