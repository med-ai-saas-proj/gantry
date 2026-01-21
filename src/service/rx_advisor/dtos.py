from src.ehr.dtos import InputEHR, InputPrescription

from ..utils.agent.dtos.generation_input import GenerationInput


class RxAdvisorInput(GenerationInput):
    ehr: InputEHR
    prescription: InputPrescription
