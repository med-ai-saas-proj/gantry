from pydantic import BaseModel


class AnswerStruct(BaseModel):
    answer: str
