import os


class EnvConsts:
    CORE_DNS = os.environ["CORE_DNS"]
    CORE_MAX_CONN = int(os.environ.get("CORE_MAX_CONN", "1"))
    CORE_MIN_CONN = int(os.environ.get("CORE_MIN_CONN", "1"))
    STAGE = os.environ["STAGE"]
    DEBUG = int(os.environ.get("DEBUG", "0"))
    GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
