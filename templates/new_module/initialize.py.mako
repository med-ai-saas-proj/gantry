"""This file initialize repositories, services, ... of ${app_name}."""

from src.shared.utils.logger import LOGGER

from . import services

from src.db.postgres.initialize import CORE_DB_SESSION_SCOPE


EXAMPLE_SERVICE = services.ExampleService(CORE_DB_SESSION_SCOPE, LOGGER)
