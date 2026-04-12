"""This file contain definition of ${app_name}'s routers."""
from gantry.auth.depends.auth import get_current_user
from gantry.auth.entities.auth_info import AuthInfo as User
from gantry.shared.utils.logger import LOGGER

from typing import Annotated

from fastapi import Body, Security, APIRouter
from fastapi.responses import JSONResponse

${app_name}_router = APIRouter(prefix="/${app_name}")
