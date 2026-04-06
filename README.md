# PolyLLM Council

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Groq](https://img.shields.io/badge/Groq-F55036?style=for-the-badge)
![OpenRouter](https://img.shields.io/badge/OpenRouter-API-orange?style=for-the-badge)

> A multi-model AI system where council models answer questions, rank each other's responses, and a custom fine-tuned chairman model synthesizes the definitive final answer.

## How It Works

A user question is sent simultaneously to three diverse council models from different AI companies. Each model then anonymously evaluates and ranks all responses, producing a peer-consensus leaderboard. A separate independent reviewer writes a per-model critique. Finally, a custom fine-tuned chairman model synthesizes the best elements into a single authoritative answer — all streamed live to the UI as each stage completes.

## Architecture

```
User Question
      │
      ▼
Stage 1 — Parallel Response Collection
      ├── Meta:   llama-4-scout-17b      (Groq)
      ├── Google: gemma-3-12b            (OpenRouter free)
      └── NVIDIA: nemotron-120b          (OpenRouter free)
      │
      ▼
Stage 2 — Anonymized Peer Ranking
      └── Same 3 models rank each other (responses labelled A/B/C)
          → Consensus leaderboard computed from aggregate scores
      │
      ▼
Stage 3 — runs in parallel
      ├── 3A: Council Review     — Moonshot AI: Kimi K2  (Groq)
      │         Per-model critique backed by peer rankings
      └── 3B: Chairman Synthesis — arsh1030/polyllm-chairman  (HuggingFace)
                Custom fine-tuned model produces the definitive answer
      │
      ▼
Final Output (streamed to frontend via Server-Sent Events)
```

## Getting Started

### Prerequisites

| Tool    | Version  |
|---------|----------|
| Python  | >= 3.10  |
| Node.js | >= 18    |
| uv      | latest   |

### Installation

```bash
git clone <repo-url>
cd "polyllm 2"

# Backend
uv sync

# Frontend
cd frontend && npm install && cd ..

# Environment
cp .env.example .env
# Edit .env and add your API keys
```

### Running

```bash
# Start both servers together
./start.sh

# Or separately:
uv run python -m backend.main     # Backend → http://localhost:8001
cd frontend && npm run dev        # Frontend → http://localhost:5173
```

## Environment Variables

| Variable             | Required | Description                                   |
|----------------------|----------|-----------------------------------------------|
| `GROQ_API_KEY`       | ✅       | Groq — Meta Llama council + Kimi K2 reviewer  |
| `OPENROUTER_API_KEY` | ✅       | OpenRouter — Gemma + Nemotron (free tier)     |
| `HF_API_TOKEN`       | ✅       | HuggingFace — custom chairman model           |
| `GEMINI_API_KEY`     | ❌       | Not used in current pipeline                  |

## Project Structure

```
backend/
├── config.py           # All config and model registry — single source of truth
├── council.py          # 3-stage pipeline orchestration
├── storage.py          # JSON conversation persistence
├── main.py             # FastAPI app and SSE streaming endpoints
├── services/
│   ├── groq.py         # Groq API client (Meta Llama, Kimi K2)
│   └── openrouter.py   # OpenRouter API client (Gemma, Nemotron)
└── prompts/
    └── templates.py    # All prompt templates — no prompts in logic files

frontend/src/
├── App.jsx             # Root — auth, conversation state, SSE streaming
├── api.js              # Backend HTTP + SSE client
└── components/
    ├── ChatInterface   # Main chat with per-stage loading indicators
    ├── Stage1/2/3      # Individual stage result panels
    ├── Sidebar         # Conversation history list
    ├── Settings        # Model configuration panel
    ├── AuthPage        # Login / register
    └── LandingPage     # Home screen

scripts/
├── collect_training_data.py  # Runs questions through council, saves outputs
├── build_dataset.py          # Converts outputs to Alpaca + ChatML fine-tuning format
├── expand_dataset.py         # Augments dataset from HuggingFace / Kaggle sources
├── generate_training_data.py # Synthetic training data generation
└── prepare_training_data.py  # Data preprocessing utilities

data/
├── conversations/    # Runtime conversation storage (auto-created, gitignored)
├── training/         # Raw council outputs collected for fine-tuning
└── dataset/          # Built fine-tuning datasets
```

## Adding a New Council Model

1. Add the model ID to `COUNCIL_MODELS` in `backend/config.py`
2. If it routes via OpenRouter, also add it to `OPENROUTER_MODEL_IDS`

No other files need to change.

## Swapping an API Provider

Edit the relevant file in `backend/services/`. The council pipeline in `council.py` is provider-agnostic.

## Training the Chairman Model

```bash
# Collect council outputs for your question bank
uv run scripts/collect_training_data.py

# Build fine-tuning datasets (Alpaca + ChatML formats)
uv run scripts/build_dataset.py

# Fine-tune — see scripts/train_chairman.ipynb
```

## Notes

- **HuggingFace chairman**: Requires `pipeline_tag: text-generation` in the model card to work via the serverless inference API. Until set, Stage 3B falls back to Kimi K2 on Groq.
- **Backend port**: 8001 (not 8000 — avoids conflicts with other local services).
- **Conversation history**: Last 6 turns injected as context for follow-up questions.
- **Stage 2 truncation**: Council responses are truncated to 800 chars in the ranking prompt to prevent payload errors with certain models.
