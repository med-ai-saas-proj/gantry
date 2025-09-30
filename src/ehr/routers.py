from src.auth.security import get_user
from src.auth.entities.user import User
from src.shared.utils.logger import LOGGER

from typing import Annotated

from fastapi import Body, Security, APIRouter
from fastapi.responses import JSONResponse
