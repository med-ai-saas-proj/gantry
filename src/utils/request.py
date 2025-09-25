from typing import Dict, List, Any
from starlette.requests import Request

from src.consts.common import MessageConsts
from src.custom_types.responses.error import CErrorResponse


class RequestUtils:
    @staticmethod
    async def get_request_body(request: Request) -> Dict:
        return await request.json()

    @staticmethod
    async def get_form_data(
        request: Request, arrayFields: List[str] = []
    ) -> Dict[str, Any]:
        """
        Extract FormData from request and return as dictionary
        Handles both regular form fields and file uploads
        """
        form_data = await request.form()
        result = {}
        for key, value in form_data.items():
            if key not in result:
                result[key] = []
            result[key].append(value)
        for key in result.keys():
            if key not in arrayFields:
                if len(result[key]) > 1:
                    raise CErrorResponse(
                        status_code=400,
                        message=MessageConsts.BAD_REQUEST,
                        errors={key: "Multiple values found for field"},
                    )
                result[key] = result[key][0]
        return result
