from src.dtos import BaseDTO, GenerateTypeAdapter


class IAddPredefinedQuestionPayload(BaseDTO):
    question: str


AddPredefinedQuestionPayload = GenerateTypeAdapter[IAddPredefinedQuestionPayload](IAddPredefinedQuestionPayload)
