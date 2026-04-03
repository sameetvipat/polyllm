"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Google Gemini API key (for direct Gemini access in Stage 3)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Council members - list of OpenRouter model identifiers
COUNCIL_MODELS = [
    "nousresearch/hermes-3-llama-3.1-405b", # Nous: Hermes 3 405B
    "meta-llama/llama-3.3-70b-instruct",    # Meta: Llama 3.3 70B Instruct
    "google/gemma-3-27b-it",                # Google: Gemma 3 27B
    "google/gemma-3-12b-it"                 # Google: Gemma 3 12B (Fallback/Diversifier)
]

# Chairman model - synthesizes final response via Google Gemini API directly
GEMINI_CHAIRMAN_MODEL = "gemini-2.5-flash"

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"
