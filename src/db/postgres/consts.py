import os


CORE_DNS = os.environ["CORE_DNS"]
CORE_MAX_CONN = int(os.environ.get("CORE_MAX_CONN", "1"))
CORE_MIN_CONN = int(os.environ.get("CORE_MIN_CONN", "1"))
