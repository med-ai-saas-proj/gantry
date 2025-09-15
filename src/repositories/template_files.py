from src.consts.db import DbConsts
from src.entities import TemplateFile
from src.repositories.postgres import PostgresRepo
from src.query_builders.postgres import BaseQueryBuilder


class TemplateFileRepository(PostgresRepo[TemplateFile]):
    query_builder = BaseQueryBuilder(table="templateFiles", schema=DbConsts.CORE_DB_SCHEMA)
