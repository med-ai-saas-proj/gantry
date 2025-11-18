from src.ai_search import ai_search_router
from src.rx_advisor import rx_advisor_router
from src.auth.routes import auth, test, api_keys
from src.ehr_summarize import ehr_summarize_router
from src.shared.consts import messages_const
from src.shared.custom_types.responses import MessagedResponse

from fastapi import APIRouter


v1_router = APIRouter(prefix="/v1")

v1_router.include_router(ehr_summarize_router)
v1_router.include_router(rx_advisor_router)
v1_router.include_router(ai_search_router)
v1_router.include_router(auth.router)
v1_router.include_router(api_keys.router)


@v1_router.get("/healthcheck", response_model=MessagedResponse)
def healthcheck():
    return MessagedResponse(status_code=200, message=messages_const.SUCCESS)
