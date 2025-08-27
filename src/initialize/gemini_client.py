from src.consts.env import EnvConsts
from src.utils.gemini_client import GeminiClient


GEMINI_LIENT = GeminiClient(EnvConsts.GEMINI_API_KEY)
