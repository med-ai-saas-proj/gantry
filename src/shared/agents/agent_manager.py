"""Module for managing agents in the system."""

from typing import Any, Callable

from pydantic_ai import Agent, AbstractToolset


class AgentConstructorContext:
    """Context for constructing agents."""

    manager: "AgentManagerService"
    agent_id: str

    def __init__(self, manager: "AgentManagerService", agent_id: str):
        """Initialize AgentConstructorContext."""
        self.manager = manager
        self.agent_id = agent_id

    def use_toolset(self, tool_id: str) -> AbstractToolset:
        """Get the toolset by its ID."""
        return self.manager.use_toolset(tool_id, agent_id=self.agent_id)

    def use_prompt(self, prompt_id: str) -> str:
        """Get the prompt by its ID."""
        return self.manager.use_prompt_for_agent(
            prompt_id, agent_id=self.agent_id
        )


class ToolsetConstructorContext:
    """Context for constructing toolsets."""

    manager: "AgentManagerService"
    toolset_id: str

    def __init__(self, manager: "AgentManagerService", toolset_id: str):
        """Initialize ToolsetConstructorContext."""
        self.manager = manager
        self.toolset_id = toolset_id

    def use_prompt(self, prompt_id: str) -> str:
        """Get the prompt by its ID."""
        return self.manager.use_prompt_for_tool(
            prompt_id, toolset_id=self.toolset_id
        )


type AgentConstructor = Callable[[AgentConstructorContext], Agent[Any, Any]]
type ToolsetConstructor = Callable[[ToolsetConstructorContext], AbstractToolset]


class AgentManagerService:
    """Service for managing agents."""

    agent_instances: dict[str, Agent[Any, Any]]
    agent_constructors: dict[str, AgentConstructor]

    toolset_instances: dict[str, AbstractToolset]
    toolset_constructors: dict[str, ToolsetConstructor]
    toolset_used_by_agents: dict[str, set[str]]

    prompts: dict[str, str]
    prompt_used_by_agents: dict[str, set[str]]
    prompt_used_by_tools: dict[str, set[str]]

    def __init__(self):
        """Initialize AgentManagementService."""
        self.prompts = {}
        self.prompt_used_by_agents = {}
        self.prompt_used_by_tools = {}

        self.agent_constructors = {}
        self.agent_instances = {}

        self.toolset_constructors = {}
        self.toolset_instances = {}
        self.toolset_used_by_agents = {}

    def initialize(self) -> None:
        """Build all registered agents and toolsets."""
        for toolset_id, constructor in self.toolset_constructors.items():
            self.toolset_instances[toolset_id] = constructor(
                ToolsetConstructorContext(self, toolset_id)
            )
        for agent_id, constructor in self.agent_constructors.items():
            self.agent_instances[agent_id] = constructor(
                AgentConstructorContext(self, agent_id)
            )


    def register_agent(
        self, agent_id: str, agent_constructor: AgentConstructor
    ) -> None:
        """Register a new agent."""
        if agent_id in self.agent_constructors:
            raise ValueError(f"Agent ID {agent_id} already registered")
        self.agent_constructors[agent_id] = agent_constructor


    def get_agent(self, agent_id):
        """Get an agent by its ID."""
        return self.agent_instances[agent_id]


    def register_toolset(
        self, tool_id: str, toolset_constructor: ToolsetConstructor
    ) -> None:
        """Register a new toolset."""
        if tool_id in self.toolset_constructors:
            raise ValueError(f"Toolset ID {tool_id} already registered")

        self.toolset_used_by_agents[tool_id] = set()
        self.toolset_constructors[tool_id] = toolset_constructor


    def use_toolset(self, tool_id: str, agent_id: str) -> AbstractToolset:
        """Get the toolset used by a specific agent."""
        if tool_id not in self.toolset_instances:
            raise ValueError(f"Toolset ID {tool_id} not found")
        self.toolset_used_by_agents[tool_id].add(agent_id)
        return self.toolset_instances[tool_id]

    def register_prompt(self, prompt_id: str, prompt_content: str) -> None:
        """Register a new prompt."""
        self.prompts[prompt_id] = prompt_content
        self.prompt_used_by_agents[prompt_id] = set()
        self.prompt_used_by_tools[prompt_id] = set()

    def update_prompt(self, prompt_id: str, prompt_content: str) -> None:
        """Update an existing prompt and refresh agents using it."""
        if prompt_id not in self.prompts:
            raise ValueError(f"Prompt ID {prompt_id} not found")

        self.prompts[prompt_id] = prompt_content

        # Refresh agents that use this prompt
        toolset_to_refresh: set[str] = set()
        agent_to_refresh: set[str] = set()
        for toolset_id in self.prompt_used_by_tools.get(prompt_id, []):
            toolset_to_refresh.add(toolset_id)
            for agent_id in self.toolset_used_by_agents.get(toolset_id, []):
                agent_to_refresh.add(agent_id)

        for agent_id in self.prompt_used_by_agents.get(prompt_id, []):
            agent_to_refresh.add(agent_id)

        for toolset_id in toolset_to_refresh:
            self.toolset_instances[toolset_id] = self.toolset_constructors[
                toolset_id
            ](ToolsetConstructorContext(self, toolset_id))
        for agent_id in agent_to_refresh:
            self.agent_instances[agent_id] = self.agent_constructors[agent_id](
                AgentConstructorContext(self, agent_id)
            )

    def use_prompt_for_agent(self, prompt_id: str, agent_id: str) -> str:
        """Get the prompt and register dependency for a specific agent."""
        if prompt_id not in self.prompts:
            raise ValueError(f"Prompt ID {prompt_id} not found")
        self.prompt_used_by_agents[prompt_id].add(agent_id)
        return self.prompts[prompt_id]

    def use_prompt_for_tool(self, prompt_id: str, toolset_id: str) -> str:
        """Get the prompt and register dependency for a specific toolset."""
        if prompt_id not in self.prompts:
            raise ValueError(f"Prompt ID {prompt_id} not found")
        self.prompt_used_by_tools[prompt_id].add(toolset_id)
        return self.prompts[prompt_id]
