from dataclasses import dataclass

from src.management.api_keys.entities import ApiKeyInfo


@dataclass
class AgentDeps:
    """Common dependencies required by agents."""

    agent_id: str
    api_key_info: ApiKeyInfo
