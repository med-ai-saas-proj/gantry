"""Service for Rx Advisor agent."""

from src.ehr.dtos import InputEHR, InputPrescription
from src.shared.utils import dict_utils
from src.ehr.custom_types import EHRDict, PrescriptionDict
from src.service.rx_advisor.agents import RX_ADVISOR_AGENT_NAME
from src.shared.agents.shared_types import AnswerStruct
from src.shared.agents.agent_manager import AgentManagerService
from src.shared.agents.agent_service import AgentService

from typing import (
    Any,
)

from pydantic import BaseModel
from pydantic_ai import Agent
from structlog.stdlib import BoundLogger


class ModelInput(BaseModel):
    """Input model for Rx Advisor agent."""

    ehr: InputEHR
    prescription: InputPrescription


class RxAdvisorService(AgentService[ModelInput, AnswerStruct]):
    """Service for Rx Advisor agent."""

    def __init__(
        self,
        logger: BoundLogger,
        agent_manager: AgentManagerService,
    ):
        """Initialize RxAdvisorService."""
        super().__init__(logger, agent_manager)

    async def initialize_agent(self) -> Agent[Any, AnswerStruct]:
        return self.agent_manager.get_agent(RX_ADVISOR_AGENT_NAME)

    async def preprocess_input(self, input: ModelInput) -> str:
        ehr = input.ehr
        prescription = input.prescription
        ehr_dict = EHRDict.from_input_ehr(ehr)
        prescription_dict = PrescriptionDict.from_input_prescription(
            prescription
        )
        prompt = self._process_ehr_and_prescription_to_prompt(
            ehr_dict, prescription_dict
        )
        return prompt

    async def store_result(
        self, user_id: str, input: ModelInput, result: AnswerStruct | None
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
