from src.db.factories import getRedis, getRedisLockManager
from src.management.api_keys.entities import ApiKeyInfo
from src.service.utils.file_storage.utils import (
    detect_file_type,
)
from src.service.utils.file_storage.models import FileType
from src.service.utils.conversation.services import ConversationService
from src.service.utils.file_storage.services import FileStorageService

from .dtos.model import (
    AudioURL as InputAudioURL,
    FileLink,
    ImageURL as InputImageURL,
    VideoURL as InputVideoURL,
    ModelInput,
    DocumentURL as InputDocumentURL,
    StreamEvent,
    StreamEvent_PartType,
    StreamEvent_PartDelta,
    StreamEvent_PartStart,
    StreamEvent_FinalResult,
    StreamEvent_ConversationStart,
)
from .dtos.generation_output import (
    ResponseStatus,
    GenerationOutput,
)
from ..file_storage.factories import getFileStorageService

import json
import asyncio
from typing import (
    AsyncIterator,
    AsyncGenerator,
)

from pydantic_ai.run import AgentRunResultEvent
from pydantic_ai.messages import (
    ModelMessage,
    AgentStreamEvent,
)


file_service = getFileStorageService()


class StreamHandler:
    new_messages: list[ModelMessage] | None

    def __init__(
        self,
        file_service: FileStorageService,
        conversation_id: int | None,
        conversation_uid: str,
        api_key_info: ApiKeyInfo,
        conversation_service: ConversationService,
    ):
        self.file_service = file_service
        self.conversation_id = conversation_id
        self.conversation_uid = conversation_uid
        self.api_key_info = api_key_info
        self.conversation_service = conversation_service
        self.new_messages = None

    async def convertAgentStream[T](
        self,
        agent_stream: AsyncIterator[AgentStreamEvent | AgentRunResultEvent[T]],
    ) -> AsyncGenerator[StreamEvent]:
        # i = 0
        yield StreamEvent_ConversationStart(
            conversation_id=self.conversation_uid
        )

        async for event in agent_stream:
            # self.logger.debug("Got new event", new_event=event)
            await asyncio.sleep(2)  # Simulate async operation
            match event.event_kind:
                case "part_start":
                    part = event.part
                    match part.part_kind:
                        case "text":
                            yield StreamEvent_PartStart(
                                part_type=StreamEvent_PartType.output,
                            )
                            if part.has_content():
                                yield StreamEvent_PartDelta().addText(
                                    delta=part.content
                                )
                        case "thinking":
                            yield StreamEvent_PartStart(
                                part_type=StreamEvent_PartType.thinking,
                            )
                            if part.has_content():
                                yield StreamEvent_PartDelta().addThinking(
                                    delta=part.content
                                )
                        case "tool-call":
                            yield StreamEvent_PartStart(
                                part_type=StreamEvent_PartType.builtin_tool_call,
                            )
                        case "builtin-tool-call":
                            yield StreamEvent_PartStart(
                                part_type=StreamEvent_PartType.builtin_tool_call,
                            )
                        case "builtin-tool-return":
                            yield StreamEvent_PartStart(
                                part_type=StreamEvent_PartType.builtin_tool_result,
                            )
                        case _:
                            pass
                case "part_delta":
                    delta = event.delta
                    match delta.part_delta_kind:
                        case "text":
                            yield StreamEvent_PartDelta().addText(
                                delta=delta.content_delta
                            )
                        case "thinking":
                            yield StreamEvent_PartDelta().addThinking(
                                delta=delta.content_delta
                            )
                        case "tool_call":
                            pass
                        case _:
                            pass
                case "part_end":
                    pass
                case "function_tool_call":
                    yield StreamEvent_PartDelta().addBuiltinToolCall(
                        tool_call_id=event.part.tool_call_id,
                        hinted_tool_name=event.part.tool_name,
                        hinted_args=event.part.args_as_json_str(),
                    )
                case "function_tool_result":
                    # Put part start to signify the end of last part
                    yield StreamEvent_PartStart(
                        part_type=StreamEvent_PartType.builtin_tool_result,
                    )
                    yield StreamEvent_PartDelta().addBuiltinToolResult(
                        tool_call_id=event.result.tool_call_id,
                        hinted_result=json.dumps(
                            event.result.content, ensure_ascii=False
                        ),
                    )
                case "builtin_tool_call":
                    yield StreamEvent_PartDelta().addBuiltinToolCall(
                        tool_call_id=event.part.tool_call_id,
                        hinted_tool_name=event.part.tool_name,
                        hinted_args=event.part.args_as_json_str(),
                    )
                case "builtin_tool_result":
                    # Put part start to signify the end of last part
                    yield StreamEvent_PartStart(
                        part_type=StreamEvent_PartType.builtin_tool_result,
                    )
                    yield StreamEvent_PartDelta().addBuiltinToolResult(
                        tool_call_id=event.result.tool_call_id,
                        hinted_result=json.dumps(
                            event.result.content, ensure_ascii=False
                        ),
                    )
                case "final_result":
                    pass
                case "agent_run_result":
                    # self.logger.debug("Got final result")
                    usage = event.result.usage()
                    yield StreamEvent_FinalResult(
                        GenerationOutput(
                            id=event.result.run_id,
                            conversation_id=self.conversation_uid,
                            status=ResponseStatus.completed,
                            output=None,
                            error=None,
                            usage={
                                "input_tokens": usage.input_tokens,
                                "output_tokens": usage.output_tokens,
                            },
                        )
                    )
                    # self.logger.debug("Result", result=result)
                    self.new_messages = event.result.new_messages()
                case _:
                    pass
