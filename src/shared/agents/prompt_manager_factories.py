from src.shared.agents.prompt_manager import PromptManager
from src.shared.agents.agent_manager_factories import getAgentManager

from functools import lru_cache


@lru_cache(1)
def getPromptManager():
    """Get PromptManager singleton."""
    return PromptManager(
        getAgentManager()
    )