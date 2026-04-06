#!/bin/bash
# Start the full PolyLLM Council stack.
#
# Usage (run from project root):
#   ./start.sh
#
# Starts:
#   - Chairman model server  on http://localhost:8002  (mlx_lm)
#   - FastAPI backend         on http://localhost:8001
#   - React frontend          on http://localhost:5173

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting PolyLLM Council..."
echo ""

echo "Starting chairman model server on http://localhost:8002..."
mlx_lm.server \
    --model "$SCRIPT_DIR/models/quantized" \
    --port 8002 &
CHAIRMAN_PID=$!

sleep 3

echo "Starting backend on http://localhost:8001..."
cd "$SCRIPT_DIR"
uv run python -m backend.main &
BACKEND_PID=$!

sleep 2

echo "Starting frontend on http://localhost:5173..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "PolyLLM Council is running."
echo "  Chairman: http://localhost:8002"
echo "  Backend:  http://localhost:8001"
echo "  Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all servers."

trap "kill $CHAIRMAN_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
