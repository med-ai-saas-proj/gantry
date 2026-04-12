from pydantic import HttpUrl
from pydantic_settings import BaseSettings


class UserLogSettings(BaseSettings):
    loki_url: HttpUrl = HttpUrl("http://localhost:3100")
