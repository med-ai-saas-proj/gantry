from pyrusult import Ok, Err, Result, ResultStatus
from gantry.db.session import AsyncSessionManager
from gantry.service.conversation import (
    Message,
    TreeConversationService,
)
from gantry.management.project.repositories import ProjectRepository
from gantry.shared.custom_types.error_exception import (
    RecoverableError,
    InternalServiceError,
)

from .settings import AiGatewaySettings

import json
import uuid
from uuid import UUID
from typing import Any, AsyncIterator
from datetime import UTC, datetime
from dataclasses import asdict

import tiktoken
from pydantic import TypeAdapter
from ag_ui.core import (
    CustomEvent,
    RunAgentInput,
    RunErrorEvent,
    SystemMessage,
    MessagesSnapshotEvent,
)
from pydantic_ai import Agent, ModelSettings, AgentRunResult
from ag_ui.core.types import Message as AGUIMessage, TextInputContent
from pydantic_ai.usage import RunUsage
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
        session_manager: AsyncSessionManager,
        project_repo: ProjectRepository,
    ) -> None:
        self.settings = settings
        self.tree_conversation_service = tree_conversation_service
        self.session_manager = session_manager
        self.project_repo = project_repo
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
        max_turns: int = 100,
        system_prompt: str | list[str] | None = None,
        reserved_tokens: int = 0,
    ) -> Result[AsyncIterator[str], ModelNotFound]:
        if model not in self.agent:
            return Err(ModelNotFound())
        # Get messages form conversation services using run_input.thread_id and run_input.parent_run_id

        conversation_uuid = UUID(run_input.thread_id)
        parent_run_id = (
            UUID(run_input.parent_run_id) if run_input.parent_run_id else None
        )
        input_message = run_input.messages
        messages_history = (
            await self.tree_conversation_service.getConversationMessages(
                conversation_uid=conversation_uuid,
                project_id=project_id,
                branch_node_id=parent_run_id,
                limit=max_turns - len(input_message),
                order_by="desc",
            )
        )

        is_new_conversation = False
        if messages_history.status == ResultStatus.Err:
            messages_history = []
            await self.tree_conversation_service.createConversation(
                project_id, {}, None, conversation_uuid
            )
            is_new_conversation = True
        else:
            messages_history = messages_history.value
            messages_history = list(reversed(messages_history))

        system_messages = []
        if system_prompt:
            if isinstance(system_prompt, str):
                system_prompt = [system_prompt]
            elif not isinstance(system_prompt, list):
                raise ValueError(
                    "system_prompt must be a string or a list of strings"
                )
            for prompt in system_prompt:
                system_messages.append(
                    SystemMessage(id=str(uuid.uuid4()), content=prompt)
                )

        if run_input.forwarded_props and isinstance(
            run_input.forwarded_props, dict
        ):
            key_of_system_prompt = {
                "system_prompt",
                "SystemPrompt",
                "system_prompts",
                "SystemPrompts",
                "system_message",
                "SystemMessage",
                "system_messages",
                "SystemMessages",
                "system_instruction",
                "SystemInstruction",
                "system_instructions",
                "SystemInstructions",
            }
            key_of_system_prompt = map(str.lower, key_of_system_prompt)

            for key in run_input.forwarded_props:
                if key.lower() in key_of_system_prompt:
                    value = run_input.forwarded_props[key]
                    if isinstance(value, str):
                        system_messages.append(
                            SystemMessage(id=str(uuid.uuid4()), content=value)
                        )
                    elif isinstance(value, list):
                        for v in value:
                            if isinstance(v, str):
                                system_messages.append(
                                    SystemMessage(
                                        id=str(uuid.uuid4()), content=v
                                    )
                                )
                    break

        # for msg in messages:
        #     print(
        #         f"Message from conversation service: {msg}, run_id: {msg.run_id}"
        #     )

        run_input.parent_run_id = (
            str(messages_history[-1].run_id)
            if messages_history
            and messages_history[-1].run_id
            and not parent_run_id
            else run_input.parent_run_id
        )

        dict_to_obj = TypeAdapter(AGUIMessage).validate_python
        aguiMessagesHistory = [
            dict_to_obj(msg.payload) for msg in messages_history
        ]

        # for msg in aguiMessagesHistory:
        #     print(
        #         f"Message from conversation service: {msg}, obj type: {type(msg)}"
        #     )

        system_messages_tokens = system_messages_tokens = sum(
            self.count_tokens(msg) for msg in system_messages
        )
        run_input.messages = system_messages + self.trimMessageContent(
            aguiMessagesHistory + input_message,
            max_turns=max_turns,
            context_window=self.settings.models[model].context_window
            - system_messages_tokens,
            reserved_tokens=(
                model_settings["max_tokens"]
                if "max_tokens" in model_settings
                else 0
            )
            + reserved_tokens,
        )

        # for msg in run_input.messages:
        #     print(
        #         f"Final Message for model input: {msg}, obj type: {type(msg)}"
        #     )

        adapter = AGUIAdapter(
            self.agent[model], run_input, manage_system_prompt="client"
        )

        async def _onComplete(run_result: AgentRunResult):
            new_messages = AGUIAdapter.dump_messages(run_result.new_messages())

            title_usage: RunUsage | None = None
            if is_new_conversation:
                generated_title = False
                # Generate a title from the first user message
                for msg in input_message:
                    if getattr(msg, "role", None) == "user":
                        content = getattr(msg, "content", None)
                        if content:
                            if isinstance(content, list):
                                text_content = " ".join(
                                    part.text
                                    for part in content
                                    if isinstance(part, TextInputContent)
                                )
                            else:
                                text_content = str(content)

                            if text_content.strip():
                                try:
                                    async with self.agent[
                                        self.settings.summary_model or model
                                    ].iter(
                                        "Generate a concise, descriptive "
                                        "title (maximum 20 words) for a "
                                        "conversation that starts with "
                                        "this message. Return ONLY the "
                                        "title text, nothing else:\n\n"
                                        f"{text_content[:1000]}"
                                    ) as agent_run:
                                        async for _ in agent_run:
                                            pass
                                        result = agent_run.result
                                        if result is not None:
                                            title = result.output.strip()
                                            title_usage = result.usage()
                                            await self.tree_conversation_service.updateConversationMetadata(
                                                conversation_uuid,
                                                project_id,
                                                {"title": title},
                                            )
                                            generated_title = True
                                except Exception:
                                    pass
                        break
                if not generated_title:
                    await self.tree_conversation_service.updateConversationMetadata(
                        conversation_uuid, project_id, {"title": "Untitled"}
                    )

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
                        for msg in input_message
                    ]
                    + [
                        Message(
                            message_uid=UUID(msg.id),
                            payload=msg,
                            run_id=run_input.run_id,
                            timestamp=datetime.now(),
                        )
                        for msg in new_messages
                    ],
                    from_node_id=parent_run_id,
                )
            )
            if res.status == ResultStatus.Err:
                yield RunErrorEvent(
                    timestamp=self.getTimestamp(),
                    message=res.value.detail
                    or "Failed to store conversation messages",
                )

            yield MessagesSnapshotEvent(
                timestamp=self.getTimestamp(),
                messages=input_message + new_messages,
            )

            usages = [{"model": model, "usage": asdict(run_result.usage())}]
            if title_usage is not None:
                usages.append(
                    {
                        "model": self.settings.summary_model or model,
                        "usage": asdict(title_usage),
                    }
                )

            yield CustomEvent(
                timestamp=self.getTimestamp(),
                name="model_usage",
                value=usages,
            )

        return Ok(
            adapter.encode_stream(
                adapter.run_stream(
                    model_settings=model_settings,
                    on_complete=_onComplete,
                )
            )
        )

    encoding = tiktoken.encoding_for_model("gpt-4o")

    @classmethod
    def count_tokens(cls, msg: AGUIMessage) -> int:
        payload = json.dumps(
            msg.model_dump(),
            ensure_ascii=False,
        )

        # approximate chat overhead
        return len(cls.encoding.encode(payload)) + 4

    @classmethod
    def trimMessageContent(
        cls,
        msgs: list[AGUIMessage],
        max_turns: int,
        context_window: int,
        reserved_tokens: int = 8000,
    ) -> list[AGUIMessage]:

        max_input_tokens = context_window - reserved_tokens

        recent_msgs = msgs[-max_turns:]

        result = []
        total_tokens = 0

        for msg in reversed(recent_msgs):
            msg_tokens = cls.count_tokens(msg)

            if total_tokens + msg_tokens > max_input_tokens:
                break

            result.insert(0, msg)
            total_tokens += msg_tokens
        return result

    @classmethod
    def getTimestamp(cls):
        return int(datetime.now(UTC).timestamp() * 1000)

    async def routeWithProjectUUID(
        self,
        model: str,
        project_uid: uuid.UUID,
        run_input: RunAgentInput,
        model_settings: ModelSettings,
        max_turns: int = 100,
        system_prompt: str | list[str] | None = None,
        reserved_tokens: int = 0,
    ) -> Result[AsyncIterator[str], ModelNotFound]:
        return await self._wrapProjectUUID(
            project_uid,
            self.route,
            model=model,
            run_input=run_input,
            model_settings=model_settings,
            system_prompt=system_prompt,
            max_turns=max_turns,
            reserved_tokens=reserved_tokens,
        )

    async def _wrapProjectUUID(
        self, project_uid: uuid.UUID, async_func, **kwargs
    ):
        async with self.session_manager.get_session() as session:
            project = await self.project_repo.getByUuid(
                session, str(project_uid)
            )
            if not project:
                raise InternalServiceError(
                    message=f"Project with UUID {project_uid} not found."
                )
            project_id = project.id
        return await async_func(project_id=project_id, **kwargs)

    def getModels(self) -> list[str]:
        return list(self.agent.keys())
