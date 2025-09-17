from src.services.postgres import PostgresService
from src.utils.dict_utils import DictUtils

import yaml
from typing import Callable
from contextlib import _GeneratorContextManager

from structlog.stdlib import BoundLogger
from pydantic_ai import Agent


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

    def _store_ehr_and_result(self, user_id: str, ehr: dict, result: dict):
        pass

    def _process_ehr(self, ehr: dict):
        processed_ehr = DictUtils.yaml_dump_prune_empty(ehr)
        self.logger.debug("Processed EHR", processed_ehr=processed_ehr)
        return processed_ehr

    async def summarize_ehr_stream(self, user_id: str, ehr: dict):
        result = {"result": ""}
        try:
            async with self.agent.run_stream(self._process_ehr(ehr)) as run:
                async for output in run.stream_text(delta=True):
                    result["result"] += output
                    yield output
        except Exception as e:
            result["error"] = str(e)
            raise e
        finally:
            self.logger.debug("Result", result=result)
            self._store_ehr_and_result(user_id, ehr, result)

    async def summarize_ehr(self, user_id: str, ehr: dict) -> str:
        # Why does this instead of run_sync?
        # Anthropic said: non-streaming Messages API requests are not expected to exceed a 10 minute timeout
        # https://docs.anthropic.com/en/api/errors#long-requests
        result = {"result": ""}
        try:
            async with self.agent.run_stream(self._process_ehr(ehr)) as run:
                async for output in run.stream_text(delta=True):
                    result["result"] += output

            return result["result"]
        except Exception as e:
            result["error"] = str(e)
            raise e
        finally:
            self.logger.debug("Result", result=result)
            self._store_ehr_and_result(user_id, ehr, result)
