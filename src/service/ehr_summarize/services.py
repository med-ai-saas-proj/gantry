from src.ehr import ehr_utils
from src.ehr.dtos import InputEHR
from src.shared.utils import dict_utils
from src.ehr.custom_types import EHRDict
from src.service.utils.agent.agent_deps import AgentDeps

from .agents import constructEhrSummarizeAgentDeps
from ..utils.agent.stream import (
    aggregateStream,
    convertAgentStream,
)
from ..utils.agent.dtos.model import ChatOutput, StreamEvent

from typing import AsyncGenerator

from pydantic_ai import Agent
from structlog.stdlib import BoundLogger


class EHRSummarizeService:
    def __init__(
        self,
        session_scope,
        logger: BoundLogger,
        agent: Agent[AgentDeps, str],
        # agent: Agent[Dep, AnswerStruct],
    ):
        self.agent = agent
        self.logger = logger

    def _ehr_to_prompt(self, ehr: EHRDict):
        processed_ehr = ehr_utils.prune_and_preprocess_input_ehr(ehr)
        ehr_str = dict_utils.yaml_dump(processed_ehr.content)
        self.logger.debug("Processed EHR", type=ehr.type, ehr_str=ehr_str)
        return ehr_str

    async def summarizeStream(
        self, user_id: str, ehr: InputEHR
    ) -> AsyncGenerator[StreamEvent]:
        model_input = [self._ehr_to_prompt(EHRDict.from_input_ehr(ehr))]

        async for event in convertAgentStream(
            self.agent.run_stream_events(
                model_input,
                deps=constructEhrSummarizeAgentDeps(
                    {"user_id": user_id}  # todo update later
                ),
            )
        ):
            yield event

    async def summarize(self, user_id: str, ehr: InputEHR) -> ChatOutput:
        result = await aggregateStream(self.summarizeStream(user_id, ehr))
        return result
