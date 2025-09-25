from src.services.postgres import PostgresService
from src.utils.dict_utils import DictUtils
from src.utils.ehr import EHRUtils
from src.custom_types.ehr import InputEHR, EHRDict
from src.custom_types.responses import SSEResponse

from typing import (
    Callable,
    Literal,
    Union,
    AsyncGenerator,
    TypedDict,
)
from contextlib import _GeneratorContextManager
from enum import Enum

from structlog.stdlib import BoundLogger
from pydantic_ai import Agent


class Event(str, Enum):
    delta = "delta"
    done = "done"


class DeltaData(TypedDict):
    d: str


class DoneData(TypedDict):
    d: Literal[""]


DataType = Union[DeltaData, DoneData]

SSEResponseContent = SSEResponse.Content[Event, DataType]


class StreamDelta(TypedDict):
    event: Literal[Event.delta]
    data: DeltaData


class StreamDone(TypedDict):
    event: Literal[Event.done]
    data: DoneData


SSEContent = Union[StreamDelta, StreamDone]


class EHRSummaryService:
    def __init__(
        self,
        session_scope: Callable[..., _GeneratorContextManager],
        logger: BoundLogger,
        agent: Agent,
    ):
        self.postgres_service = PostgresService(session_scope=session_scope)
        self.agent = agent
        self.logger = logger

    def _store_ehr_and_result(
        self, user_id: str, ehr_dict: EHRDict, result: dict
    ):
        pass

    def _ehr_to_prompt(self, ehr: EHRDict):
        processed_ehr = EHRUtils.prune_and_preprocess_input_ehr(ehr)
        ehr_str = DictUtils.yaml_dump(processed_ehr.content)
        self.logger.debug("Processed EHR", type=ehr.type, ehr_str=ehr_str)
        return ehr_str

    async def summarize_ehr_stream(
        self, user_id: str, ehr: InputEHR
    ) -> AsyncGenerator[SSEContent, None]:
        ehr_dict = EHRDict.from_input_ehr(ehr)
        result = {"result": ""}
        try:
            prompt = self._ehr_to_prompt(ehr_dict)
            async with self.agent.run_stream(prompt) as run:
                async for output in run.stream_text(delta=True):
                    # yield StreamDelta(event=Event.delta, data={"d": output})
                    yield {"event": Event.delta, "data": {"d": output}}
                    result["result"] += output
            # yield StreamDone(event=Event.done, data={"d": ""})
            yield {"event": Event.done, "data": {"d": ""}}
        except Exception as e:
            result["error"] = str(e)
            raise e
        finally:
            self.logger.debug("Result", result=result)
            self._store_ehr_and_result(user_id, ehr_dict, result)

    async def summarize_ehr(self, user_id: str, ehr: InputEHR) -> str:
        # Why does this instead of run_sync?
        # Anthropic said: non-streaming Messages API requests are not expected to exceed a 10 minute timeout
        # https://docs.anthropic.com/en/api/errors#long-requests
        final_result = ""
        async for text_chunk in self.summarize_ehr_stream(user_id, ehr):
            final_result += text_chunk["data"]["d"]
        return final_result
