from gantry.service.conversation import (
    TreeConversationService,
    ConversationNotFoundError,
)

from .settings import AiGatewaySettings

from uuid import UUID
from typing import Any, AsyncIterator

from pyrusult import Ok, Err, Result, ResultStatus
from ag_ui.core import RunAgentInput
from pydantic_ai import Agent, ModelSettings
from pydantic_ai.ag_ui import run_ag_ui
from pydantic_ai.models import Model, fallback, infer_model
from pydantic_ai.ui.ag_ui import AGUIAdapter
from pydantic_ai.providers import Provider, infer_provider_class


def _meta_infer_provider(api_key: str | None, base_url: str | None):
    def _infer_provider(provider: str) -> Provider[Any]:
        provider_class = infer_provider_class(provider)
        return provider_class(api_key=api_key, base_url=base_url)

    return _infer_provider


class AiGatewayService:
    def __init__(
        self,
        settings: AiGatewaySettings,
        tree_conversation_service: TreeConversationService,
    ) -> None:
        self.settings = settings
        self.tree_conversation_service = tree_conversation_service
        self.agent: dict[str, Agent] = {}
        models: dict[str, Model] = {}
        for model_name, specs in settings.models.items():
            models[model_name] = infer_model(
                f"{specs.provider}:{specs.model_id}",
                _meta_infer_provider(
                    specs.api_key.get_secret_value()
                    if specs.api_key is not None
                    else None,
                    specs.base_url.encoded_string()
                    if specs.base_url is not None
                    else None,
                ),
            )
            models[model_name]

        for model_name, specs in settings.models.items():
            model = models[model_name]
            if specs.fallback is not None:
                model = fallback.FallbackModel(
                    models[model_name],
                    *(
                        models[fallback_model_name]
                        for fallback_model_name in specs.fallback
                    ),
                )

            self.agent[model_name] = Agent(model)

    async def ficl(
        self,
        model: str,
        project_id: int,
        run_input: RunAgentInput,
        model_settings: ModelSettings,
    ) -> Result[AsyncIterator[str], ConversationNotFoundError]:
        # Get messages form conversation services using run_input.thread_id and run_input.parent_run_id
        if run_input.parent_run_id is not None:
            messages = (
                await self.tree_conversation_service.getConversationMessages(
                    conversation_uid=UUID(run_input.thread_id),
                    project_id=project_id,
                )
            )

            messages = (
                [] if messages.status == ResultStatus.Err else messages.value
            )
        else:
            messages = []

        return Ok(
            run_ag_ui(
                self.agent[model],
                run_input,
                message_history=AGUIAdapter.load_messages(
                    [msg.payload for msg in messages]
                ),
                model_settings=model_settings,
                # usage_limits={},
                manage_system_prompt="client",
            )
        )
