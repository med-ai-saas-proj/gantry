"""This file is the entrypoint for debugging."""

import argparse

import uvicorn
from uvicorn.config import LOGGING_CONFIG


def getMainApp():
    from src.main.app import main_app

    return main_app


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--port", required=False, help="port", default="8000")
    ap.add_argument(
        "-w", "--workers", required=False, help="number workers", default="1"
    )
    args = vars(ap.parse_args())
    LOGGING_CONFIG["formatters"]["default"]["fmt"] = (
        "%(asctime)s [%(name)s] %(levelprefix)s %(message)s"
    )
    uvicorn.run(
        getMainApp,
        host="0.0.0.0",
        port=int(args["port"]),
        workers=int(args["workers"]),
        env_file=".env",
    )
