#!/bin/bash
# Start the local chairman model server.
#
# Prerequisites:
#   uv add mlx-lm        (or: pip install mlx-lm)
#
# Usage (run from project root):
#   ./scripts/start_chairman.sh
#
# The server will:
#   - Load the quantized model from models/quantized/
#   - Serve an OpenAI-compatible API at http://localhost:8002

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL="$SCRIPT_DIR/../models/quantized"
PORT=8002

echo "Starting chairman model server on port $PORT ..."
echo "Model: $MODEL"
echo "Press Ctrl+C to stop."
echo ""

mlx_lm.server \
    --model "$MODEL" \
    --port "$PORT"
