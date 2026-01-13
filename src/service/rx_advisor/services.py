from src.ehr.dtos import InputEHR, InputPrescription
from src.shared.utils import dict_utils
from src.ehr.custom_types import EHRDict, PrescriptionDict
from src.service.utils.agent.dtos.model import ChatOutput

from ..utils.agent.stream import aggregateStream, convertAgentStream

from pydantic_ai import Agent
from structlog.stdlib import BoundLogger


class RxAdvisorService:
    def __init__(
        self,
        session_manager,
        # session_scope: Callable[..., _GeneratorContextManager],
        logger: BoundLogger,
        agent: Agent[None, str],
    ):
        # self.postgres_service = PostgresService(session_scope=session_scope)
        self.agent = agent
        self.logger = logger

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
        user_id: str,
        ehr: InputEHR,
        prescription: InputPrescription,
    ):
        model_input = [
            self._process_ehr_and_prescription_to_prompt(
                EHRDict.from_input_ehr(ehr),
                PrescriptionDict.from_input_prescription(prescription),
            )
        ]
        async for event in convertAgentStream(
            self.agent.run_stream_events(model_input)
        ):
            yield event

    async def generateAdvice(
        self, user_id: str, ehr: InputEHR, prescription: InputPrescription
    ) -> ChatOutput:
        return await aggregateStream(
            self.generateAdviceStream(user_id, ehr, prescription)
        )
