# PolyLLM - Collective Agentic Intelligence

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![OpenRouter](https://img.shields.io/badge/OpenRouter-API-orange?style=for-the-badge)
![Gemini](https://img.shields.io/badge/Google_Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white)

The PolyLLM Council is an advanced research platform designed to evaluate and verify Large Language Model (LLM) outputs. By utilizing a "Council" of diverse models system identifies contradictions, validates facts against live data, and provides a "Chairman" synthesized response with a calibrated confidence score.

## How It Works

1. **Stage 1**: Your query is sent to multiple LLMs in parallel
2. **Stage 2**: Each model reviews and ranks the other models' responses (anonymized)
3. **Stage 3**: The chairman model reviews all responses and provides its own authoritative answer

## Installation

### Prerequisites

- Python 3.10+
- Node.js 16+
- [uv](https://docs.astral.sh/uv/) package manager

### Setup

1. **Clone the repository**

   ```bash
   git clone <your-repo-url>
   cd llm-council
   ```

2. **Install dependencies**

   ```bash
   # Backend
   uv sync

   # Frontend
   cd frontend
   npm install
   cd ..
   ```

3. **Configure API keys**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your API keys:
   - **OpenRouter API Key**: Get from [openrouter.ai](https://openrouter.ai/)
   - **Gemini API Key**: Get from [Google AI Studio](https://aistudio.google.com/app/apikey)

4. **Run the application**

   ```bash
   # Terminal 1 - Backend
   uv run -m backend.main

   # Terminal 2 - Frontend
   cd frontend
   npm run dev
   ```

5. **Open in browser**
   ```
   http://localhost:5173
   ```

## Configuration

Edit `backend/config.py` to customize the council models:

```python
COUNCIL_MODELS = [
    "openai/gpt-4",
    "anthropic/claude-3.5-sonnet",
    "google/gemini-pro",
    # Add more models from OpenRouter
]

GEMINI_CHAIRMAN_MODEL = "gemini-2.0-flash-exp"
```

## Tech Stack

- **Backend**: FastAPI, Python 3.10+
- **Frontend**: React + Vite
- **APIs**: OpenRouter, Google Gemini
- **Storage**: Local JSON files

## License

MIT
