"""Rx Advisor Service."""

from src.ehr.dtos import InputEHR, InputPrescription
from src.shared.utils import dict_utils
from src.ehr.custom_types import EHRDict, PrescriptionDict

from .agents import constructRxAdvisorAgentDeps
from ..utils.agent.stream import aggregateStream, convertAgentStream
from ..utils.agent.agent_deps import AgentDeps
from ..utils.agent.dtos.model import ChatOutput
from ...management.api_keys.entities import ApiKeyInfo
from ..utils.agent.models.models_service import ModelsService

from pydantic_ai import Agent
from structlog.stdlib import BoundLogger


class RxAdvisorService:
    """Service to provide prescription advice based on EHR and new prescriptions."""

    def __init__(
        self,
        session_manager,
        logger: BoundLogger,
        agent: Agent[AgentDeps, str],
        models_service: ModelsService,
    ):
        self.agent = agent
        self.logger = logger
        self.models_service = models_service

    def _store_ehr_and_result(
        self,
        user_id: str,
        ehr: EHRDict,
        prescription: PrescriptionDict,
        result: dict,
    ):
        pass

    def _process_ehr_and_prescription_to_prompt(
        self, ehr: EHRDict, prescription: PrescriptionDict
    ):
        processed_ehr = dict_utils.yaml_dump_prune_empty(ehr.content)
        processed_prescription = dict_utils.yaml_dump_prune_empty(
            prescription.content
        )
        self.logger.debug("Processed EHR", processed_ehr=processed_ehr)
        self.logger.debug(
            "Processed Prescription",
            processed_prescription=processed_prescription,
        )
        return f"""Patient's EHR:
{processed_ehr}

New Prescription:
{processed_prescription}"""

    async def generateAdviceStream(
        self,
        api_key_info: ApiKeyInfo,
        model_id: str,
        ehr: InputEHR,
        prescription: InputPrescription,
    ):
        model, model_config = self.models_service.get_model(model_id)
        model_input = [
            self._process_ehr_and_prescription_to_prompt(
                EHRDict.from_input_ehr(ehr),
                PrescriptionDict.from_input_prescription(prescription),
            )
        ]
        async for event in convertAgentStream(
            self.agent.run_stream_events(
                model_input,
                model=model,
                deps=constructRxAdvisorAgentDeps(
                    api_key_info,
                    model_config,
                ),
            )
        ):
            yield event

    async def generateAdvice(
        self,
        api_key_info: ApiKeyInfo,
        model_id: str,
        ehr: InputEHR,
        prescription: InputPrescription,
    ) -> ChatOutput:
        return await aggregateStream(
            self.generateAdviceStream(api_key_info, model_id, ehr, prescription)
        )
