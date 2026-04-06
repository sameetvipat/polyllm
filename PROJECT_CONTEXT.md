# LLM Council — Project Context

## What It Is

A multi-model AI system where multiple open-source LLMs act as "council members" — each independently answers a question, then each model ranks the other models' responses. A designated fine-tuned "chairman" model reads all responses and rankings and synthesizes a single final answer.

**Goal:** Explore whether a collaborative multi-model approach produces better, more balanced answers than a single LLM alone — leveraging model diversity to reduce individual model bias and blind spots.

---

## Core Pipeline
```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER QUERY                                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│               STAGE 1 — Council Deliberation                        │
│                                                                     │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│   │  LLaMA 4 Scout  │  │  Gemma 3 12B    │  │  Nemotron 120B  │   │
│   │  17B (Groq)     │  │  (OpenRouter)   │  │  (OpenRouter)   │   │
│   └────────┬────────┘  └────────┬────────┘  └────────┬────────┘   │
│            │                    │                     │            │
│            └──────────── parallel ────────────────────┘            │
│                                                                     │
│   Each model independently answers the query (max_tokens=2048)     │
│   On failure: fallback to llama-3.3-70b-versatile (Groq)           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  responses[]
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│               STAGE 2 — Anonymised Peer Ranking                     │
│                                                                     │
│   responses[] ──► Anonymiser ──► Response A, Response B, Response C│
│                   (identity hidden; label_to_model map stored)      │
│                                                                     │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│   │  LLaMA 4 Scout  │  │  Gemma 3 12B    │  │  Nemotron 120B  │   │
│   │  ranks A, B, C  │  │  ranks A, B, C  │  │  ranks A, B, C  │   │
│   └────────┬────────┘  └────────┬────────┘  └────────┬────────┘   │
│            │                    │                     │            │
│            └──────────── parallel ────────────────────┘            │
│                                                                     │
│   Raw rankings parsed via regex → average rank position computed   │
│   De-anonymised using label_to_model map → aggregate_rankings[]    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  ranked_responses[] + aggregate_rankings[]
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│               STAGE 3A — Council Review                             │
│                                                                     │
│   Model: openai/gpt-oss-20b:free  (OpenRouter)                     │
│   Input: all Stage 1 responses + Stage 2 rankings                  │
│   Output: structured review / critique (max_tokens=2048)           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  review text
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│               STAGE 3B — Chairman Synthesis                         │
│                                                                     │
│   Model: sameetvipat/polyllm-chairman                               │
│          (Mistral-7B-Instruct-v0.3 + LoRA, local MLX :8002)        │
│   Input: Stage 1 responses + Stage 2 rankings + Stage 3A review    │
│   Output: final synthesized answer (max_tokens=1024)               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FINAL RESPONSE TO USER                           │
│                                                                     │
│   Returned as: { stage1, stage2, stage3, metadata }                │
│   Persisted to: data/conversations/<id>.json                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Council Models

| Model ID | Provider | API |
|----------|----------|-----|
| `meta-llama/llama-4-scout-17b-16e-instruct` | Meta | Groq |
| `google/gemma-3-12b-it:free` | Google | OpenRouter (free) |
| `nvidia/nemotron-3-super-120b-a12b:free` | NVIDIA | OpenRouter (free) |

**Fallback model** (substitutes for any council model that fails Stage 1): `llama-3.3-70b-versatile` (Groq)

## Stage 3A Reviewer

- **Model:** `openai/gpt-oss-20b:free` (OpenRouter — independent from all council members)

## Chairman Model

- **Base:** `mistralai/Mistral-7B-Instruct-v0.3`
- **Fine-tuning:** LoRA adapters trained on custom (council responses + rankings → ideal synthesis) dataset
- **Published:** `sameetvipat/polyllm-chairman` on Hugging Face
- **Inference:** Local Apple Silicon via `mlx_lm` (`http://localhost:8002`)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 + FastAPI (port 8001) |
| Frontend | React 18 + Vite (port 5173) |
| Async HTTP | `httpx.AsyncClient` (singleton per service) |
| Cloud APIs | Groq API, OpenRouter API |
| Local Inference | MLX (`mlx_lm`) on Apple Silicon |
| Storage | JSON flat-file (`data/conversations/`) |
| Markdown | `react-markdown` + `remark-gfm` + `rehype-highlight` |

---

## Key Modules

| File | Role |
|------|------|
| `backend/council.py` | Core orchestration — all 3 stages |
| `backend/services/groq.py` | Groq client + singleton + retry |
| `backend/services/openrouter.py` | OpenRouter client + singleton |
| `backend/storage.py` | JSON persistence + settings cache (30 s TTL) |
| `backend/main.py` | FastAPI app, lifespan, CORS |
| `frontend/src/App.jsx` | State management, message flow, toasts |
| `frontend/src/components/chat/` | Stage1, Stage2, Stage3, ChatInterface |
| `frontend/src/components/layout/Sidebar.jsx` | History, search, skeleton |

---

## Key Design Decisions

- **Anonymisation in Stage 2** — prevents models from biasing rankings toward known competitors
- **LoRA chairman** — custom fine-tune specifically for the synthesis/aggregation task
- **Singleton `httpx` clients** — avoids ~100–200 ms SSL handshake per request
- **Settings cache (30 s TTL)** — prevents repeated disk reads across a council run
- **Graceful degradation** — run continues if one model fails; partial results returned

## Token Budgets

| Stage | max_tokens |
|-------|-----------|
| Stage 1 (council responses) | 2048 |
| Stage 2 (rankings) | 1024 |
| Stage 3A (council review) | 2048 |
| Stage 3B (chairman verdict) | 1024 |

---

## Current Status

| Feature | Status |
|---------|--------|
| Full 3-stage pipeline | Working |
| Frontend (Stage 1/2/3 views) | Working |
| LoRA chairman model (MLX) | Working |
| Conversation history + search | Working |
| Copy buttons, markdown rendering | Working |
| Error toasts, skeleton loading | Working |
