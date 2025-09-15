from contextlib import _GeneratorContextManager
from typing import Callable, List
import json

from src.consts.predefined_questions import PredefinedQuestionConsts
from src.custom_types.responses import CErrorResponse
from src.dtos.add_predefined_questions import IAddPredefinedQuestionPayload
from src.entities import Regulation, PredefinedQuestion, RegulationReference
from src.repositories import RegulationRepo, PredefinedQuestionRepo
from src.repositories.regulation_references import RegulationReferenceRepo
from src.services import PostgresService
from src.utils.gemini_client import GeminiClient
from src.utils.embedding_client import EmbeddingClient
from src.utils.logger import LOGGER


class PredefinedQuestionService:
    def __init__(self, session_scope: Callable[..., _GeneratorContextManager], gemini_client: GeminiClient):
        self.postgres_service = PostgresService(session_scope=session_scope)
        self.session_scope = session_scope
        self.gemini_client = gemini_client
        self.embedding_client = EmbeddingClient()

    async def find_best_match_regulation(
        self, question: str, best_match_regulation: Regulation | None, regulations: List[Regulation]
    ):
        for regulation in regulations:
            # Tạo prompt để đánh giá regulation có liên quan đến question không
            if best_match_regulation is None:
                # Lần đầu tiên, chỉ cần kiểm tra xem regulation có liên quan không
                relevance_prompt = PredefinedQuestionConsts.first_prompt.format(
                    question=question,
                    regulationTitle=regulation["title"],
                    regulationContent=regulation["content"],
                )
                response = await self.gemini_client.generate_text(relevance_prompt, temperature=0.1)
                response = self.gemini_client._clean_json_response(response)
                result = json.loads(response)

                if result.get("isRelevant", False) and result.get("confidenceScore", 0) > 0.5:
                    best_match_regulation = regulation

            else:
                response = await self.gemini_client.generate_text(
                    PredefinedQuestionConsts.comparison_prompt, temperature=0.1
                )
                response = self.gemini_client._clean_json_response(response)
                result = json.loads(response)

                if result.get("newIsBetter", False) and result.get("confidenceScore", 0) > 0.6:
                    best_match_regulation = regulation
        return best_match_regulation

    async def generate_answer(self, question: str, best_match_regulation: Regulation):
        # Generate answer based on best_match_regulation
        answer_prompt = PredefinedQuestionConsts.answer_generation_prompt.format(
            question=question,
            regulationTitle=best_match_regulation["title"],
            regulationContent=best_match_regulation["content"],
        )

        answer_response = await self.gemini_client.generate_text(answer_prompt, temperature=0.3)
        answer_response = self.gemini_client._clean_json_response(answer_response)
        answer_result = json.loads(answer_response)

        generated_answer = answer_result.get("answer", None)
        if generated_answer is None:
            return None, None, "Generated answer is empty"
        detail_references = answer_result.get("regulationReferences", [])
        return generated_answer, detail_references, None

    async def generate_predefined_question(self, question: str):
        regulations = await self.postgres_service.get_all(RegulationRepo)
        best_match_regulation = await self.find_best_match_regulation(question, None, regulations)
        if best_match_regulation is None:
            raise CErrorResponse(http_code=400, status_code=400, message="No regulation found for this question")
        generated_answer, regulation_references, error = await self.generate_answer(question, best_match_regulation)
        if error:
            raise CErrorResponse(http_code=400, status_code=400, message=error)
        # Generate embedding for the question
        question_embedding = self.embedding_client.generate_embedding(question)
        predefined_question: PredefinedQuestion = {
            "question": question,
            "answer": generated_answer,
            "questionEmbedding": question_embedding,
            "referenceText": json.dumps(regulation_references),
        }
        return predefined_question, best_match_regulation

    async def add_predefined_question(self, payload: IAddPredefinedQuestionPayload):
        # Generate embedding for the question
        with self.session_scope():
            predefined_question, best_match_regulation = await self.generate_predefined_question(payload["question"])
            inserted_predefined_question = await self.postgres_service.insert(
                PredefinedQuestionRepo, predefined_question
            )
            regulation_reference: RegulationReference = {
                "questionId": inserted_predefined_question["id"],
                "regulationId": best_match_regulation["id"],
            }
            await self.postgres_service.insert(RegulationReferenceRepo, regulation_reference)

    async def add_auto_predefined_questions_for_regulation(self, regulation: Regulation, max_questions: int = 30):
        # Generate questions using LLM
        questions_prompt = PredefinedQuestionConsts.generate_questions_prompt.format(
            regulationTitle=regulation["title"], regulationContent=regulation["content"], maxQuestions=max_questions
        )

        response = await self.gemini_client.generate_text(questions_prompt, temperature=0.7)
        response = self.gemini_client._clean_json_response(response)
        LOGGER.info(f"Generated questions: {response}")
        result = json.loads(response)

        generated_questions = result.get("questions", [])
        if not generated_questions:
            raise CErrorResponse(http_code=400, status_code=400, message="No questions generated for this regulation")

        with self.session_scope():
            # Generate answer for each question
            for question_text in generated_questions:
                LOGGER.info(f"Generating predefined question for question: {question_text}")
                answer, detail_references, error = await self.generate_answer(question_text, regulation)
                if error:
                    raise CErrorResponse(http_code=400, status_code=400, message=error)

                question_embedding = self.embedding_client.generate_embedding(question_text)
                inserted_predefined_question = await self.postgres_service.insert(
                    PredefinedQuestionRepo,
                    {
                        "question": question_text,
                        "questionEmbedding": question_embedding,
                        "answer": answer,
                        "referenceText": json.dumps(detail_references),
                    },
                    True,
                )
                regulation_reference: RegulationReference = {
                    "questionId": inserted_predefined_question["id"],
                    "regulationId": regulation["id"],
                }
                await self.postgres_service.insert(RegulationReferenceRepo, regulation_reference)
