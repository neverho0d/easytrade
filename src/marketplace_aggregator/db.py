# src/marketplace_aggregator/db.py
import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel  # Import SQLModel base


# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set!")

# Create the async engine
# echo=True is useful for debugging SQL, remove in production
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Create a configured "Session" class - name convention change in recent SQLAlchemy
# AsyncSessionFactory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
AsyncSessionFactory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency function to get an async session."""
    async with AsyncSessionFactory() as session:
        yield session


async def create_db_and_tables():
    """Creates database tables based on SQLModel metadata."""
    async with engine.begin() as conn:
        # await conn.run_sync(SQLModel.metadata.drop_all) # Use cautiously!
        await conn.run_sync(SQLModel.metadata.create_all)
    print("Database tables created (if they didn't exist).")


if __name__ == "__main__":
    import asyncio

    print("Attempting to create database tables...")
    # Need to import models for metadata registration
    from marketplace_aggregator.models import product  # noqa
    from marketplace_aggregator.models import variable_product  # noqa
    from marketplace_aggregator.models import promotional_rule  # noqa
    from marketplace_aggregator.models import listing  # noqa

    asyncio.run(create_db_and_tables())
    print("Table creation process finished.")
