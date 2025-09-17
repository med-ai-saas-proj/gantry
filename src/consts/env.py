import os


class EnvConsts:
    CORE_DNS = os.environ["CORE_DNS"]
    CORE_MAX_CONN = int(os.environ.get("CORE_MAX_CONN", "1"))
    CORE_MIN_CONN = int(os.environ.get("CORE_MIN_CONN", "1"))
    STAGE = os.environ["STAGE"]  # PROD, DEV, LOCAL
    DEBUG = int(os.environ.get("DEBUG", "0"))

    ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
    GOOGLE_PROGRAMMATIC_SEARCH_API_KEY = os.environ[
        "GOOGLE_PROGRAMMABLE_SEARCH_API_KEY"
    ]
    GOOGLE_PROGRAMMATIC_SEARCH_CX = os.environ["GOOGLE_PROGRAMMABLE_SEARCH_CX"]

    CRAWLER_MAX_CONCURRENT = int(os.environ.get("CRAWLER_MAX_CONCURRENT", "8"))
