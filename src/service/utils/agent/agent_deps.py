from src.management.api_keys.entities import ApiKeyInfo
from src.service.utils.models.model_config import ModelConfig

from dataclasses import dataclass


@dataclass
class AgentDeps:
    """Common dependencies required by agents."""

    agent_id: str
    api_key_info: ApiKeyInfo
    model_config: ModelConfig
