"""This file initialize repositories, services, ... of ${app_name}."""

from . import services

from gantry.shared.utils.logger import LOGGER
from gantry.db.postgres.initialize import CORE_DB_SESSION_SCOPE


EXAMPLE_SERVICE = services.ExampleService(CORE_DB_SESSION_SCOPE, LOGGER)
