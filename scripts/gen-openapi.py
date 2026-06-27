from gantry.main.app import internal_app

import json
import argparse
import subprocess
from datetime import datetime

from fastapi.openapi.utils import get_openapi


def main():
    parser = argparse.ArgumentParser(
        description="Generate SDKs from OpenAPI schema"
    )
    parser.add_argument(
        "--commit-hash",
        type=str,
        default=None,
        help="Git commit hash to include in the SDK output path (e.g. sdk/<hash>/python)",
    )
    args = parser.parse_args()

    prefix = (
        f"sdk/{args.commit_hash}"
        if args.commit_hash
        else f"sdk/{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )

    openapi_schema = get_openapi(
        title=internal_app.title,
        version=internal_app.version,
        openapi_version=internal_app.openapi_version,
        description=internal_app.description,
        routes=internal_app.routes,
    )

    # create a temporary directory to store the OpenAPI schema
    subprocess.run(["mkdir", "-p", "./temp"], check=True)

    # Write the schema dictionary to a file
    with open("./temp/openapi.json", "w") as f:
        json.dump(openapi_schema, f, indent=2)

    # remove old SDK directories if they exist
    subprocess.run(["rm", "-rf", f"{prefix}/python"], check=True)
    subprocess.run(["rm", "-rf", f"{prefix}/typescript"], check=True)
    subprocess.run(["rm", "-rf", f"{prefix}/go"], check=True)

    # generate python client SDK using openapi-generator-cli
    subprocess.run(
        [
            "openapi-generator-cli",
            "generate",
            "-i",
            "./temp/openapi.json",
            "-g",
            "python",
            "-o",
            f"{prefix}/python",
        ],
        check=True,
    )

    # generate typescript client SDK using openapi-generator-cli
    subprocess.run(
        [
            "openapi-generator-cli",
            "generate",
            "-i",
            "./temp/openapi.json",
            "-g",
            "typescript-fetch",
            "-o",
            f"{prefix}/typescript",
        ],
        check=True,
    )

    # generate go client SDK using openapi-generator-cli
    subprocess.run(
        [
            "openapi-generator-cli",
            "generate",
            "-i",
            "./temp/openapi.json",
            "-g",
            "go",
            "-o",
            f"{prefix}/go",
        ],
        check=True,
    )

    # clean up the temporary directory
    subprocess.run(["rm", "-rf", "./temp"], check=True)


if __name__ == "__main__":
    main()
