"""This file initialize repositories, services, ... of ${app_name}."""

from src.shared.utils.logger import LOGGER
from src.db.postgres.initialize import CORE_DB_SESSION_SCOPE

from . import services


EXAMPLE_SERVICE = services.ExampleService(CORE_DB_SESSION_SCOPE, LOGGER)
