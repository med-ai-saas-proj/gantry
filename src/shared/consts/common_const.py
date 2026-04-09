import os


ROOT_FOLDER = os.path.abspath(
    os.path.join(os.path.abspath(__file__), 3 * "../")
)
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
REQUEST_ID_HEADER = "x-request-id"
APP_NAME = "gantry"
APP_VERSION = "0.0.3"
