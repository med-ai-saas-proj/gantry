from src.entities import RegulationReference
from src.query_builders.postgres import BaseQueryBuilder
from src.repositories.postgres import PostgresRepo


class RegulationReferenceRepo(PostgresRepo[RegulationReference]):
    query_builder = BaseQueryBuilder(table="regulationReferences", schema="tailm")
