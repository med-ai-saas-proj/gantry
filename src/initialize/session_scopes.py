from sqlalchemy.orm import Session
from src.consts.env import EnvConsts
from src.db.connectors.postgres import PostgresConnectorPool
from src.db.sessions import BaseSession


CORE_DB_SESSION_SCOPE = BaseSession[Session](
    pool=PostgresConnectorPool(
        dns=EnvConsts.CORE_DNS, max_conn=EnvConsts.CORE_MAX_CONN, min_conn=EnvConsts.CORE_MIN_CONN
    )
).generate_session_scope_func()
