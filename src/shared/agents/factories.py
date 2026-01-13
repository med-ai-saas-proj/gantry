from src.shared.agents.agent_manager import AgentManagerService

from functools import lru_cache


@lru_cache(1)
def getAgentManager():
    return AgentManagerService()