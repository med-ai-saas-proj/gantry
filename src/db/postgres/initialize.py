from . import consts
from ..session import BaseSession
from .connector import PostgresConnectorPool

from sqlalchemy.orm import Session


CORE_DB_SESSION_SCOPE = BaseSession[Session](
    pool=PostgresConnectorPool(
        dns=consts.CORE_DNS,
        max_conn=consts.CORE_MAX_CONN,
        min_conn=consts.CORE_MIN_CONN,
    )
).generate_session_scope_func()
