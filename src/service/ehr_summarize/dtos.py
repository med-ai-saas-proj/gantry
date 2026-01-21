from src.ehr.dtos import InputEHR

from ..utils.agent.dtos.generation_input import GenerationInput


class EHRSummarizeInput(GenerationInput):
    input_ehr: InputEHR
