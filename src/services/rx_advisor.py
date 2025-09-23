from src.services.postgres import PostgresService
from src.utils.dict_utils import DictUtils
from src.agents.shared_types import AnswerStruct

from typing import Callable
from contextlib import _GeneratorContextManager

from structlog.stdlib import BoundLogger
from pydantic_ai import Agent
from pydantic import ValidationError


class RxAdvisorService:
    def __init__(
        self,
        session_scope: Callable[..., _GeneratorContextManager],
        logger: BoundLogger,
        agent: Agent[None, AnswerStruct],
    ):
        self.postgres_service = PostgresService(session_scope=session_scope)
        self.agent = agent
        self.logger = logger

    def _store_ehr_and_result(
        self, user_id: str, ehr: dict, prescription: dict, result: dict
    ):
        pass

    def _process_ehr_and_prescription(self, ehr: dict, prescription: dict):
        processed_ehr = DictUtils.yaml_dump_prune_empty(ehr)
        processed_prescription = DictUtils.yaml_dump_prune_empty(prescription)
        self.logger.debug("Processed EHR", processed_ehr=processed_ehr)
        self.logger.debug(
            "Processed Prescription",
            processed_prescription=processed_prescription,
        )
        return f"""Patient's EHR:
{processed_ehr}

New Prescription:
{processed_prescription}"""

    async def generate_advice_stream(
        self, user_id: str, ehr: dict, prescription: dict
    ):
        result = {"result": ""}
        try:
            async with self.agent.run_stream(
                self._process_ehr_and_prescription(ehr, prescription)
            ) as run:
                async for output, end in run.stream_responses():
                    try:
                        validated_output = await run.validate_response_output(
                            output,
                            allow_partial=not end,
                        )
                    except ValidationError:
                        continue
                    answer = validated_output["answer"]
                    new_response = answer[len(agent_result) :]
                    yield new_response
                    agent_result = answer
        except Exception as e:
            result["error"] = str(e)
            raise e
        finally:
            self.logger.debug("Result", result=result)
            self._store_ehr_and_result(user_id, ehr, prescription, result)

    async def generate_advice(
        self, user_id: str, ehr: dict, prescription: dict
    ) -> str:
        # Why does this instead of run_sync?
        # Anthropic said: non-streaming Messages API requests are not expected to exceed a 10 minute timeout
        # https://docs.anthropic.com/en/api/errors#long-requests
        res = ""
        async for output in self.generate_advice_stream(
            user_id, ehr, prescription=prescription
        ):
            res += output
        return res
