import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from .models import Base

load_dotenv()

# Async engine for FastAPI
async_engine = create_async_engine(
    os.getenv("DATABASE_URL"),
    echo=True,  # Set to False in production
    future=True
)

# Sync engine for Alembic migrations
sync_engine = create_engine(
    os.getenv("DATABASE_URL_SYNC"),
    echo=True
)

# Async session maker
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Sync session maker
SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False
)

async def get_async_db():
    """Dependency for FastAPI to get async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def get_sync_db():
    """Get sync database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def create_tables():
    """Create database tables"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)