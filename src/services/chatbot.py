from contextlib import _GeneratorContextManager
from typing import Callable, List, Optional, Dict, Any
import json
from sqlalchemy import text

from src.custom_types.responses import CErrorResponse
from src.services import PostgresService
from src.utils.embedding_client import EmbeddingClient
from src.utils.logger import LOGGER


class ChatbotService:
    def __init__(self, session_scope: Callable[..., _GeneratorContextManager]):
        self.postgres_service = PostgresService(session_scope=session_scope)
        self.session_scope = session_scope
        self.embedding_client = EmbeddingClient()
        self.similarity_threshold = 0.6

    def _process_user_query(self, query: str) -> str:
        """Process and validate user input"""
        if not query or not query.strip():
            raise CErrorResponse(http_code=400, status_code=400, message="Query cannot be empty")

        cleaned_query = query.strip()

        if len(cleaned_query) < 3:
            raise CErrorResponse(http_code=400, status_code=400, message="Query too short (minimum 3 characters)")

        if len(cleaned_query) > 500:
            raise CErrorResponse(http_code=400, status_code=400, message="Query too long (maximum 500 characters)")

        return cleaned_query

    async def _vector_similarity_search(self, query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """PostgreSQL pgvector search for similar predefined questions"""
        try:
            # Raw SQL for pgvector cosine similarity search
            embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

            sql_query = f"""
            SELECT 
                id,
                question,
                answer,
                "referenceText",
                "createdAt",
                1 - ("questionEmbedding" <=> '{embedding_str}'::vector) as "similarityScore"
            FROM tailm."predefinedQuestions"
            -- WHERE "questionEmbedding" IS NOT NULL
            ORDER BY "questionEmbedding" <=> '{embedding_str}'::vector
            -- LIMIT {limit}
            """

            with self.session_scope() as session:
                print(sql_query)
                result = session.execute(text(sql_query))
                rows = result.fetchall()

                search_results = []
                for row in rows:
                    search_results.append(
                        {
                            "id": row[0],
                            "question": row[1],
                            "answer": row[2],
                            "referenceText": json.loads(row[3]) if row[3] else [],
                            "createdAt": row[4],
                            "similarityScore": float(row[5]),
                        }
                    )
                return search_results

        except Exception as e:
            raise e

    def _check_similarity_threshold(self, search_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Check if best match meets similarity threshold"""
        if not search_results:
            return None

        best_match = search_results[0]
        if best_match["similarityScore"] >= self.similarity_threshold:
            return best_match

        return None

    async def _get_suggested_questions(self, search_results: List[Dict[str, Any]]) -> List[str]:
        """Generate 3 suggested questions from search results or popular questions"""
        suggestions = []

        # Use positions 2-4 from search results if available
        for i in range(1, min(4, len(search_results))):
            if len(suggestions) < 3:
                suggestions.append(search_results[i]["question"])

        # Fill remaining slots with popular questions if needed
        if len(suggestions) < 3:
            try:
                popular_sql = text(
                    """
                SELECT question 
                FROM tailm."predefinedQuestions" 
                ORDER BY "createdAt" DESC 
                LIMIT 5
                """
                )

                with self.session_scope() as session:
                    result = session.execute(popular_sql)
                    popular_rows = result.fetchall()

                    for row in popular_rows:
                        if len(suggestions) >= 3:
                            break
                        question = row[0]
                        if question not in suggestions:
                            suggestions.append(question)

            except Exception as e:
                LOGGER.error(f"Failed to get popular questions: {str(e)}")

        return suggestions[:3]

    def _build_response(
        self, found_answer: bool, best_match: Optional[Dict[str, Any]], suggested_questions: List[str], user_query: str
    ) -> Dict[str, Any]:
        """Build structured chatbot response"""
        if found_answer and best_match:
            return {
                "foundAnswer": True,
                "answer": best_match["answer"],
                "sourceReference": best_match["referenceText"],
                "confidenceScore": best_match["similarityScore"],
                "suggestedQuestions": suggested_questions,
                "userQuery": user_query,
            }
        else:
            return {
                "foundAnswer": False,
                "answer": "Xin lỗi, tôi không tìm thấy thông tin phù hợp với câu hỏi của bạn. Vui lòng tham khảo các câu hỏi gợi ý bên dưới hoặc liên hệ trực tiếp với bộ phận hỗ trợ.",
                "sourceReference": [],
                "confidenceScore": 0.0,
                "suggestedQuestions": suggested_questions,
                "userQuery": user_query,
            }

    async def process_chat_query(self, user_query: str) -> Dict[str, Any]:
        """Main chatbot processing pipeline"""
        try:
            # Step 1: Process user query
            cleaned_query = self._process_user_query(user_query)

            # Step 2: Generate embedding for query
            query_embedding = self.embedding_client.generate_embedding(cleaned_query)

            # LOGGER.info(query_embedding)
            # Step 3: Vector similarity search
            search_results = await self._vector_similarity_search(query_embedding, limit=5)
            LOGGER.info(len(search_results))

            # Step 4: Check similarity threshold
            best_match = self._check_similarity_threshold(search_results)

            # Step 5: Get suggested questions
            suggested_questions = await self._get_suggested_questions(search_results)

            # Step 6: Build response
            response = self._build_response(
                found_answer=best_match is not None,
                best_match=best_match,
                suggested_questions=suggested_questions,
                user_query=cleaned_query,
            )

            return response

        except CErrorResponse:
            raise
        except Exception as e:
            LOGGER.error(f"Chatbot processing failed: {str(e)}")
            raise CErrorResponse(http_code=500, status_code=500, message="Internal chatbot error")
