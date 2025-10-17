import os


STAGE = os.environ["STAGE"]  # PROD, DEV, LOCAL
DEBUG = int(os.environ.get("DEBUG", "0"))

# ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
