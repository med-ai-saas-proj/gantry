#! /bin/bash
ruff check --fix --select I -q "$@"
ruff format -q "$@"