from typing import Callable
from contextlib import _GeneratorContextManager

from src.dtos.add_regulations import IAddRegulationForm
from src.repositories import RegulationRepo
from src.services import PostgresService
from src.services.predefined_questions import PredefinedQuestionService
from src.utils.document_reader import DocumentReader
from src.custom_types.responses import CErrorResponse


class RegulationService:

    def __init__(
        self,
        session_scope: Callable[..., _GeneratorContextManager],
        predefined_question_service: PredefinedQuestionService,
    ):
        self.postgres_service = PostgresService(session_scope=session_scope)
        self.session_scope = session_scope
        self.predefined_question_service = predefined_question_service

    async def add_regulation(self, body: IAddRegulationForm, auto_generate_questions: bool = True):
        content = body["content"]
        if not isinstance(content, str):
            content_bytes = await content.read()
            try:
                extracted_content = await DocumentReader.extract_content(content_bytes)
            except Exception as e:
                raise CErrorResponse(
                    http_code=400, status_code=400, message=f"Failed to process document content: {str(e)}"
                )
            body["content"] = extracted_content
        with self.session_scope():
            record = body.copy()
            record.pop("autoGenerateQuestionsCount")
            regulation = await self.postgres_service.insert(
                repo=RegulationRepo,
                record=record,
                returning=True,
            )
            # Auto-generate predefined questions if enabled and service available
            if auto_generate_questions:
                await self.predefined_question_service.add_auto_predefined_questions_for_regulation(
                    regulation, max_questions=body["autoGenerateQuestionsCount"]
                )
                return {"regulation": regulation}
            return {"regulation": regulation}
