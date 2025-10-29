from pydantic import Field, BaseModel


class CreateApiKeyRequest(BaseModel):
    permissions: list[str] = Field(..., description="Scopes associated with the API key")