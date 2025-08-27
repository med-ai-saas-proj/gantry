from fastapi import APIRouter
from fastapi.responses import JSONResponse
from starlette.requests import Request

from src.initialize.services import CHATBOT_SERVICE
from src.utils.request import RequestUtils


router = APIRouter()


@router.post("/chat")
async def chat_query(request: Request):
    """Process chatbot query with RAG vector search"""
    payload = await RequestUtils.get_request_body(request)
    user_query = payload.get("query", "").strip()

    if not user_query:
        return JSONResponse(status_code=400, content={"message": "Query is required", "error": "MISSING_QUERY"})

    result = await CHATBOT_SERVICE.process_chat_query(user_query)
    return JSONResponse(status_code=200, content={"message": "Success", "data": result})


@router.get("/chat/suggestions")
async def get_popular_questions():
    """Get popular predefined questions for display"""
    try:
        # Get recent popular questions
        popular_questions = await CHATBOT_SERVICE._get_suggested_questions([])

        return JSONResponse(
            status_code=200,
            content={
                "message": "Success",
                "data": {"popular_questions": popular_questions, "total": len(popular_questions)},
            },
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "Failed to get popular questions", "error": str(e)})
