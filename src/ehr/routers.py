from src.auth.depends.auth import get_user
from src.auth.entities.auth_info import AuthInfo as User
from src.shared.utils.logger import LOGGER

from typing import Annotated

from fastapi import Body, Security, APIRouter
from fastapi.responses import JSONResponse
