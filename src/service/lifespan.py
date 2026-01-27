
from src.service.utils.agent.factories import getModelsService, getPromptService

from fastapi import FastAPI


async def startup(app: FastAPI):
    # Startup code here
    prompt_service = getPromptService()
    await prompt_service.load_prompts()
    model_service = getModelsService()
    await model_service.load_model_config()


async def shutdown(app: FastAPI):
    # Cleanup code here
    pass
