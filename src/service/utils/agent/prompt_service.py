from src.db.session import AsyncSessionManager
from src.service.utils.agent.agent_deps import AgentDeps

from typing import TypeVar

from pydantic_ai import RunContext, ToolDefinition
from structlog.stdlib import BoundLogger
from pydantic_ai.tools import ToolPrepareFunc


AgentDepsT = TypeVar("AgentDepsT", bound=AgentDeps)


class PromptService:
    """Service to manage and provide prompts for agents and tools."""

    prompts: dict[str, str]

    def __init__(
        self, session_manager: AsyncSessionManager, logger: BoundLogger
    ):
        self.prompts = {}

    def add_prompt(self, name: str, prompt: str):
        """Adds or updates a prompt by name."""
        self.prompts[name] = prompt

    def remove_prompt(self, name: str):
        """Removes a prompt by name."""
        if name in self.prompts:
            del self.prompts[name]

    def get_agent_instruction(self, ctx: RunContext[AgentDepsT]) -> str:
        """Returns the instruction prompt for the agent based on its ID."""
        return self.prompts.get(ctx.deps.agent_id, "Default Instruction")

    def get_tool_instruction[DepsT](self, tool_id) -> ToolPrepareFunc[DepsT]:
        """Returns a prepare function that sets the tool's description based on stored prompts."""

        async def wrapper(
            ctx: RunContext[DepsT], tool_def: ToolDefinition
        ) -> ToolDefinition | None:
            prompt = self.prompts.get(f"{tool_id}", "Default Tool Instruction")
            tool_def.description = prompt
            return tool_def

        return wrapper

    async def load_prompts(self):
        """Load prompts from the database into the service."""
        # Placeholder for loading prompts from a database
        pass
