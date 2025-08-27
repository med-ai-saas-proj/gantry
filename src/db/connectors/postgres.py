import psycopg2

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import QueuePool

from src.utils.logger import LOGGER

# pyodbc.pooling = False


class PostgresConnectorPool:
    def __init__(
        self,
        dns: str,
        max_conn: int = 1,
        min_conn: int = 1,
    ):
        self.dns = dns
        self.max_conn = max_conn
        self.min_conn = min_conn
        self.engine = create_engine(
            # DNS,
            "postgresql+psycopg2://",
            poolclass=QueuePool,
            pool_pre_ping=True,
            pool_size=self.max_conn - self.min_conn,
            max_overflow=self.min_conn,
            pool_timeout=60 * 60,
            creator=self.__get_conn__,
        )
        try:
            session = self.get()
            self.put(session)
            LOGGER.info("Successfully create connection...")
        except Exception as e:
            raise Exception(f"Could not create connection to {self.dns}", e)

    def __get_conn__(self):
        c = psycopg2.connect(self.dns)
        return c

    def get(self) -> Session:
        return Session(bind=self.engine.connect())

    @classmethod
    def put(cls, session):
        session.close()

    @classmethod
    def commit(cls, session):
        session.commit()

    @classmethod
    def rollback(cls, session):
        session.rollback()


# import asyncio
#
# import aioodbc
# from sqlalchemy.connectors.pyodbc import PyODBCConnector
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# from sqlalchemy.pool import AsyncAdaptedQueuePool
#
# from src.utils.logger import LOGGER
#
# PyODBCConnector.fast_executemany = True
#
#
# class SQLServerConnectorPool:
#     def __init__(self, dns, max_conn, min_conn):
#         self.dns = dns
#         self.max_conn = max_conn
#         self.min_conn = min_conn
#         self.engine = create_async_engine(
#             # DNS,
#             "mssql+aioodbc://",
#             poolclass=AsyncAdaptedQueuePool,
#             pool_pre_ping=True,
#             pool_size=self.max_conn - self.min_conn,
#             max_overflow=self.min_conn,
#             pool_timeout=60 * 60,
#             async_creator=self.__get_conn__,
#             fast_executemany=True,
#             use_insertmanyvalues=False
#         )
#         # try:
#         loop = asyncio.get_event_loop()
#         async_session = loop.run_until_complete(self.get())
#         loop.run_until_complete(self.put(async_session))
#         LOGGER.info("Successfully create connection...")
#         # except Exception as e:
#         #     raise Exception(f"Could not create connection to {dns}", e)
#         #     pass
#
#     async def __get_conn__(self):
#         c = await aioodbc.connect(dsn=self.dns)
#         return c
#
#     async def get(self) -> AsyncSession:
#         async_session = AsyncSession(self.engine)
#         return async_session
#
#     @classmethod
#     async def put(cls, async_session: AsyncSession):
#         await async_session.close()
