#!/usr/bin/env bash
# Start a local Ollama >= 0.35 server for the run (CPU only, one model at a time).
# Uses `ollama` on PATH unless OLLAMA_BIN is set. Does not assume an install path.
set -euo pipefail
if [[ -z "${OLLAMA_BIN:-}" ]]; then
  if ! command -v ollama >/dev/null 2>&1; then
    echo "ollama is not on PATH. Install Ollama 0.35.1, or set OLLAMA_BIN." >&2
    exit 1
  fi
  OLLAMA_BIN=$(command -v ollama)
fi
if [[ -n "${OLLAMA_MODELS:-}" ]]; then
  export OLLAMA_MODELS
fi
export OLLAMA_HOST=${OLLAMA_HOST:-127.0.0.1:11434}
export OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_NUM_PARALLEL=1 OLLAMA_KEEP_ALIVE=30m
if curl -sf "http://$OLLAMA_HOST/api/version" >/dev/null; then echo "ollama already running"; exit 0; fi
setsid nohup "$OLLAMA_BIN" serve > "${OLLAMA_LOG:-/tmp/ollama-serve.log}" 2>&1 < /dev/null &
for i in $(seq 1 30); do curl -sf "http://$OLLAMA_HOST/api/version" && echo && exit 0; sleep 1; done
echo "ollama did not start" >&2; exit 1
