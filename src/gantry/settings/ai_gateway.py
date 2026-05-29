from typing import Annotated

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings


class ModelSpec(BaseSettings):
    provider: Annotated[
        str,
        Field(
            description="Check pydantic provider. https://pydantic.dev/docs/ai/models/overview/"
        ),
    ]
    model_id: Annotated[str, Field(description="Model ID, e.g. gpt-5.2")]
    api_key: Annotated[
        SecretStr | None, Field(description="Should be in .env instead of toml")
    ] = None
    base_url: Annotated[
        HttpUrl | None, Field(description="Provider's base url")
    ] = None
    fallback: Annotated[
        list[str] | None, Field(description="Fallback model")
    ] = None
    context_window: Annotated[
        int,
        Field(
            description="Model's context window. Used for AGUI message trimming."
        ),
    ]


class AiGatewaySettings(BaseSettings):
    models: Annotated[
        dict[str, ModelSpec],
        Field(
            description="Mapping `what you call the model from your application` -> Model's spec"
        ),
    ] = {}
