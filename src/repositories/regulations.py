from src.consts.db import DbConsts
from src.entities import Regulation
from src.repositories.postgres import PostgresRepo
from src.query_builders.postgres import BaseQueryBuilder


class RegulationRepo(PostgresRepo[Regulation]):
    query_builder = BaseQueryBuilder(table="regulations", schema=DbConsts.CORE_DB_SCHEMA)
