"""This file contain definition of ${app_name}'s routers."""
from src.auth.security import get_current_user
from src.auth.entities.user import User
from src.shared.utils.logger import LOGGER

from typing import Annotated

from fastapi import Body, Security, APIRouter
from fastapi.responses import JSONResponse

${app_name}_router = APIRouter(prefix="/${app_name}")