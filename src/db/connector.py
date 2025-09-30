from abc import ABC

from sqlalchemy.orm import Session


# pyodbc.pooling = False


class BaseConnectorPool(ABC):
    def get(self) -> Session: ...

    @classmethod
    def put(cls, session: Session): ...

    @classmethod
    def commit(cls, session: Session): ...

    @classmethod
    def rollback(cls, session: Session): ...


# import asyncio
#
# import aioodbc
# from sqlalchemy.connectors.pyodbc import PyODBCConnector
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# from sqlalchemy.pool import AsyncAdaptedQueuePool
#
# from src.main.utils.logger import LOGGER
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
