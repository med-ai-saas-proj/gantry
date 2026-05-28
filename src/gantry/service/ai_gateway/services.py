from gantry.service.conversation import (
    Message,
    TreeConversationService,
)
from gantry.shared.custom_types.error_exception import RecoverableError

from .settings import AiGatewaySettings

from uuid import UUID
from typing import Any, AsyncIterator
from datetime import UTC, datetime

from pydantic import TypeAdapter
from pyrusult import Ok, Err, Result, ResultStatus
from ag_ui.core import BaseEvent, EventType, RunAgentInput
from pydantic_ai import Agent, ModelSettings, AgentRunResult
from ag_ui.core.types import Message as AGUIMessage
from pydantic_ai.models import Model, fallback, infer_model
from pydantic_ai.ui.ag_ui import AGUIAdapter
from pydantic_ai.providers import Provider, infer_provider_class


def _meta_infer_provider(api_key: str | None, base_url: str | None):
    def _infer_provider(provider: str) -> Provider[Any]:
        provider_class = infer_provider_class(provider)
        return provider_class(api_key=api_key, base_url=base_url)

    return _infer_provider


class ModelNotFound(RecoverableError):
    status = 404
    title = "Model not found"
    detail = "Model not found"


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

    async def route(
        self,
        model: str,
        project_id: int,
        run_input: RunAgentInput,
        model_settings: ModelSettings,
    ) -> Result[AsyncIterator[str], ModelNotFound]:
        if model not in self.agent:
            return Err(ModelNotFound())
        # Get messages form conversation services using run_input.thread_id and run_input.parent_run_id

        conversation_uuid = UUID(run_input.thread_id)
        parent_run_id = (
            UUID(run_input.parent_run_id) if run_input.parent_run_id else None
        )
        messages = await self.tree_conversation_service.getConversationMessages(
            conversation_uid=conversation_uuid,
            project_id=project_id,
            branch_node_id=parent_run_id,
        )

        if messages.status == ResultStatus.Err:
            messages = []
            await self.tree_conversation_service.createConversation(
                project_id, {}, None, conversation_uuid
            )
        else:
            messages = messages.value

        dict_to_obj = TypeAdapter(AGUIMessage).validate_python
        messages = [dict_to_obj(msg.payload) for msg in messages]

        for msg in messages:
            print(
                f"Message from conversation service: {msg}, obj type: {type(msg)}"
            )
        run_input.messages = messages + run_input.messages

        adapter = AGUIAdapter(
            self.agent[model], run_input, manage_system_prompt="client"
        )

        async def _onComplete(run_result: AgentRunResult):
            res = (
                await self.tree_conversation_service.storeConversationMessages(
                    conversation_uuid,
                    project_id,
                    [
                        Message(
                            message_uid=UUID(msg.id),
                            payload=msg,
                            run_id=run_input.run_id,
                            timestamp=datetime.now(),
                        )
                        for msg in AGUIAdapter.dump_messages(
                            run_result.new_messages()
                        )
                    ],
                    from_node_id=parent_run_id,
                )
            )
            if res.status == ResultStatus.Err:
                yield BaseEvent(
                    type=EventType.RUN_ERROR,
                    timestamp=self.getTimestamp(),
                    raw_event=res.value,
                )

        return Ok(
            adapter.encode_stream(
                adapter.run_stream(
                    model_settings=model_settings,
                    on_complete=_onComplete,
                )
            )
        )

    @classmethod
    def getTimestamp(cls):
        return int(datetime.now(UTC).timestamp() * 1000)
