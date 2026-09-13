#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_BIN="${CODEX_PYTHON_BIN:-$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3}"
cd "$PROJECT_DIR"
if [[ $# -eq 0 ]]; then set -- all; fi
exec "$PY_BIN" reproduce.py "$@"
