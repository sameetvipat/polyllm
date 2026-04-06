"""OpenRouter API client — aggregator for Google, NVIDIA, and other council models."""

# ─── Imports ──────────────────────────────────────────────────────────────────

import asyncio
import logging
import httpx
from typing import List, Dict, Any, Optional

from ..config import OPENROUTER_API_KEY, OPENROUTER_API_URL

logger = logging.getLogger(__name__)


# ─── Shared client ────────────────────────────────────────────────────────────

_client: Optional[httpx.AsyncClient] = None

def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=60.0)
    return _client


# ─── Functions ────────────────────────────────────────────────────────────────

async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 4096,
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter.

    Retries up to 2 times on 429 rate-limit responses with exponential backoff.

    Args:
        model: OpenRouter model identifier (e.g. "google/gemma-3-12b-it:free")
        messages: List of {role, content} message dicts
        max_tokens: Maximum tokens in the response

    Returns:
        Dict with 'content' key, or None if all attempts fail
    """
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json',
    }
    payload = {'model': model, 'messages': messages, 'max_tokens': max_tokens}
    max_attempts = 3
    client = _get_client()

    try:
        for attempt in range(max_attempts):
            response = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)

            if response.status_code == 429:
                if attempt < max_attempts - 1:
                    backoff = 2 ** attempt
                    retry_after = response.headers.get('retry-after')
                    snippet = response.text.replace('\n', ' ')[:180]
                    logger.warning(
                        'OpenRouter rate limited for %s; retry-after=%s; waiting %ds; details=%s',
                        model, retry_after or 'n/a', backoff, snippet,
                    )
                    await asyncio.sleep(backoff)
                    continue

                logger.error('OpenRouter rate limited for %s; max retries reached', model)
                return None

            response.raise_for_status()
            content = response.json()['choices'][0]['message'].get('content')
            return {'content': content}

    except Exception as e:
        logger.error('OpenRouter query failed for %s: %s', model, e)
        return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]],
    max_tokens: int = 4096,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple OpenRouter models in parallel.

    Args:
        models: List of OpenRouter model identifiers
        messages: Shared message list sent to every model
        max_tokens: Maximum tokens in each response

    Returns:
        Dict mapping model ID → response dict (or None if failed)
    """
    tasks = [query_model(model, messages, max_tokens=max_tokens) for model in models]
    results = await asyncio.gather(*tasks)
    return dict(zip(models, results))
