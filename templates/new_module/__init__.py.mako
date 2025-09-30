% if has_router:
from .routers import ${app_name}_router

__all__ = ["${app_name}_router"]
% endif