import os
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine,async_sessionmaker
from sqlalchemy.orm import  DeclarativeBase
from typing import AsyncGenerator

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    connect_args={
        "server_settings": {"application_name": "your_app"},
        "ssl": "require"  # <--- THIS IS THE FIX
    },
)

AsyncSesssionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSesssionLocal() as session:
        try:
            yield session
        finally:
            await session.close()