from src.initialize.gemini_client import GEMINI_LIENT
from src.initialize.session_scopes import CORE_DB_SESSION_SCOPE
from src.services import RegulationService, PredefinedQuestionService
from src.services.chatbot import ChatbotService


PREDEFINED_QUESTION_SERVICE = PredefinedQuestionService(session_scope=CORE_DB_SESSION_SCOPE, gemini_client=GEMINI_LIENT)
REGULATION_SERVICE = RegulationService(
    session_scope=CORE_DB_SESSION_SCOPE, predefined_question_service=PREDEFINED_QUESTION_SERVICE
)
CHATBOT_SERVICE = ChatbotService(session_scope=CORE_DB_SESSION_SCOPE)
