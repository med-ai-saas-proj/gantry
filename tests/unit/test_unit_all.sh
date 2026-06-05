#!/usr/bin/env bash
set -euo pipefail

mapfile -t unit_tests < <(
  find src packages -type f \( -name '*_test.py' -o -name 'test.py' \) \
    -not -path '*/__pycache__/*' \
    | sort
)

if [[ ${#unit_tests[@]} -eq 0 ]]; then
  echo 'No source-adjacent unit tests found.' >&2
  exit 1
fi

exec uv run --group dev pytest "${unit_tests[@]}" "$@"
