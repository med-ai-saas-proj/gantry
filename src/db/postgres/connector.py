from src.shared.utils.logger import LOGGER

from ..connector import BaseConnectorPool

import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import QueuePool


class PostgresConnectorPool(BaseConnectorPool):
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
