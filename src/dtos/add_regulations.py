from typing import Annotated
from fastapi import UploadFile
from pydantic import Field
from src.dtos.base import BaseDTO, GenerateTypeAdapter


class IAddTemplateFileForm(BaseDTO):
    title: str
    content: str


class IAddRegulationForm(BaseDTO):
    title: str
    content: str | UploadFile
    autoGenerateQuestionsCount: Annotated[int, Field(default=30)]


AddRegulationForm = GenerateTypeAdapter[IAddRegulationForm](IAddRegulationForm)
