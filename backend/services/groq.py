"""Groq API client — OpenAI-compatible, used for council Stages 1, 2, and 3A."""

# ─── Imports ──────────────────────────────────────────────────────────────────

import asyncio
import logging
import httpx
from typing import List, Dict, Any, Optional

from ..config import GROQ_API_KEY, GROQ_API_URL

logger = logging.getLogger(__name__)


# ─── Shared client ────────────────────────────────────────────────────────────

_client: Optional[httpx.AsyncClient] = None

def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=45.0)
    return _client


# ─── Functions ────────────────────────────────────────────────────────────────

async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 4096,
    retries: int = 1,
) -> Optional[Dict[str, Any]]:
    """
    Query a single Groq model and return its response.

    Retries once on transient failures before returning None.

    Args:
        model: Groq model identifier (e.g. "meta-llama/llama-4-scout-17b-16e-instruct")
        messages: List of {role, content} message dicts
        max_tokens: Maximum tokens in the response
        retries: Number of retry attempts after an initial failure

    Returns:
        Dict with 'content' key, or None if all attempts fail
    """
    client = _get_client()
    for attempt in range(retries + 1):
        try:
            response = await client.post(
                GROQ_API_URL,
                headers={
                    'Authorization': f'Bearer {GROQ_API_KEY}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': model,
                    'messages': messages,
                    'max_tokens': max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data['choices'][0]['message']['content']
            return {'content': content}
        except Exception as e:
            if attempt < retries:
                logger.warning('Groq query failed for %s (attempt %d), retrying: %s', model, attempt + 1, e)
                await asyncio.sleep(0.5)
            else:
                logger.error('Groq query failed for %s after %d attempt(s): %s', model, retries + 1, e)
                return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]],
    max_tokens: int = 4096,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple Groq models in parallel.

    Args:
        models: List of Groq model identifiers
        messages: Shared message list sent to every model
        max_tokens: Maximum tokens in each response

    Returns:
        Dict mapping model ID → response dict (or None if failed)
    """
    tasks = [query_model(model, messages, max_tokens=max_tokens) for model in models]
    results = await asyncio.gather(*tasks)
    return dict(zip(models, results))
