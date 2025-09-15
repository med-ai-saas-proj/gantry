from src.entities import PredefinedQuestion
from src.query_builders.postgres import BaseQueryBuilder
from src.repositories.postgres import PostgresRepo


class PredefinedQuestionRepo(PostgresRepo[PredefinedQuestion]):
    query_builder = BaseQueryBuilder(table="predefinedQuestions", schema="tailm")
    JSON_FIELDS = ["referenceText"]
