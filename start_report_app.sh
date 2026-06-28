#!/bin/bash
# Start the Maintenance Fund Report web app (uv-managed environment)
set -euo pipefail

cd "$(dirname "$0")/maintenance_app"

export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-}"
export PORT="${PORT:-8765}"

# Reuse existing venv; create and install deps only on first run
if [[ ! -d .venv ]]; then
  uv venv .venv
  uv pip install -r requirements.txt --python .venv/bin/python
elif ! .venv/bin/python -c "import numpy, matplotlib, fastapi, markdown" &>/dev/null; then
  echo "Repairing broken virtualenv dependencies..."
  uv pip install -r requirements.txt --python .venv/bin/python
fi

PYTHON=".venv/bin/python"

echo "Starting server at http://localhost:${PORT}"
echo "Ollama endpoint: ${OLLAMA_BASE_URL}"
exec uv run --python "${PYTHON}" python app.py
