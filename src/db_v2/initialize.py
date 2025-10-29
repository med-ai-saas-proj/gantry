from sqlalchemy.ext.asyncio import create_async_engine

from src.db_v2.session import AsyncSessionManager

from dotenv import load_dotenv
import os
load_dotenv()

DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "main_database")

DB_ASYNC_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

async_engine = create_async_engine(DB_ASYNC_URL, echo=True)

session_manager = AsyncSessionManager(async_engine)