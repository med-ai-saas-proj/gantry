from src.consts.db import DbConsts
from src.entities import BrokerCredentials
from src.query_builders.sqlserver import SqlserverQueryBuilder
from src.repositories import SqlserverRepo


class BrokerCredentialsRepo(SqlserverRepo[BrokerCredentials]):
    query_builder = SqlserverQueryBuilder(table="brokerCredentials", schema=DbConsts.CORE_DB_SCHEMA)
    json_columns = ["credentials"]
