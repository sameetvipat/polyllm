"""Application configuration — all values pulled from environment variables.

Import constants from here; never read os.getenv() in other modules.
"""

# ─── Imports ──────────────────────────────────────────────────────────────────

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / '.env')


# ─── API Keys ─────────────────────────────────────────────────────────────────

GROQ_API_KEY: str = os.getenv('GROQ_API_KEY', '')
OPENROUTER_API_KEY: str = os.getenv('OPENROUTER_API_KEY', '')
HF_API_TOKEN: str = os.getenv('HF_API_TOKEN', '')


# ─── API Endpoints ────────────────────────────────────────────────────────────

GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'
OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions'
CUSTOM_CHAIRMAN_API_URL = (
    'https://router.huggingface.co/hf-inference/models/sameetvipat/polyllm-chairman'
)

# Local mlx-lm server — start with: scripts/start_chairman.sh
LOCAL_CHAIRMAN_URL = 'http://localhost:8002/v1/chat/completions'
LOCAL_CHAIRMAN_MODEL = str(Path(__file__).resolve().parent.parent / 'models' / 'quantized')


# ─── Council Model Registry ───────────────────────────────────────────────────

# To add a new council model: add it here and to OPENROUTER_MODEL_IDS if it
# routes via OpenRouter. No other files need to change.

COUNCIL_MODELS = [
    'meta-llama/llama-4-scout-17b-16e-instruct',  # Meta      — Groq
    'google/gemma-3-12b-it:free',                 # Google    — OpenRouter (free)
    'nvidia/nemotron-3-super-120b-a12b:free',      # NVIDIA    — OpenRouter (free)
]

# Models routed to OpenRouter instead of Groq
OPENROUTER_MODEL_IDS: set = {
    'google/gemma-3-12b-it:free',
    'nvidia/nemotron-3-super-120b-a12b:free',
    'openai/gpt-oss-20b:free',               # OpenAI OSS — OpenRouter (free)
}

# Stage 3A reviewer — independent from all council members (OpenAI OSS via OpenRouter)
REVIEW_MODEL = 'openai/gpt-oss-20b:free'

# Fallback — substitutes for any council model that fails Stage 1
FALLBACK_MODEL = 'llama-3.3-70b-versatile'


# ─── Storage ──────────────────────────────────────────────────────────────────

DATA_DIR = str(Path(__file__).resolve().parent.parent / 'data' / 'conversations')
