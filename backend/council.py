"""3-stage LLM Council orchestration.

Stages:
  1. Parallel response collection from all council models
  2. Anonymized peer ranking — each model scores the others
  3A. Council review — independent reviewer critiques each model
  3B. Chairman synthesis — custom HF model produces the final answer
"""

# ─── Imports ──────────────────────────────────────────────────────────────────

import asyncio
import logging
import re
import httpx
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

from .services import groq, openrouter
from .services.groq import query_model
from .prompts.templates import (
    build_ranking_prompt,
    build_council_review_prompt,
    build_chairman_hf_prompt,
    build_chairman_fallback_prompt,
    build_title_prompt,
)
from .config import (
    HF_API_TOKEN,
    CUSTOM_CHAIRMAN_API_URL,
    LOCAL_CHAIRMAN_URL,
    LOCAL_CHAIRMAN_MODEL,
    REVIEW_MODEL,
    OPENROUTER_MODEL_IDS,
)
from . import storage


# ─── Constants ────────────────────────────────────────────────────────────────

FIRST_LABEL_ASCII = 65   # ord('A') — labels Stage 1 responses as A, B, C, …
MAX_TITLE_LENGTH = 50
MAX_RESPONSE_CHARS = 800  # Stage 2 truncation — prevents payload errors


# ─── Shared chairman client ───────────────────────────────────────────────────

_chairman_client: Optional[httpx.AsyncClient] = None

def _get_chairman_client() -> httpx.AsyncClient:
    global _chairman_client
    if _chairman_client is None:
        _chairman_client = httpx.AsyncClient(timeout=120.0)
    return _chairman_client


# ─── Routing ─────────────────────────────────────────────────────────────────

async def _query_mixed_models(
    models: List[str],
    messages: List[Dict[str, str]],
    max_tokens: int = 4096,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Route each model to Groq or OpenRouter and query all in parallel.

    Models listed in OPENROUTER_MODEL_IDS are sent to OpenRouter;
    all others go to Groq.

    Args:
        models: Council model identifiers
        messages: Shared message list sent to every model
        max_tokens: Token budget passed to Groq (OpenRouter uses its defaults)

    Returns:
        Dict mapping model ID → response dict (or None if failed)
    """
    groq_models = [m for m in models if m not in OPENROUTER_MODEL_IDS]
    or_models   = [m for m in models if m in OPENROUTER_MODEL_IDS]

    tasks = []
    if groq_models:
        tasks.append(groq.query_models_parallel(groq_models, messages, max_tokens=max_tokens))
    if or_models:
        tasks.append(openrouter.query_models_parallel(or_models, messages, max_tokens=max_tokens))

    results = await asyncio.gather(*tasks)
    combined: Dict[str, Optional[Dict[str, Any]]] = {}
    for result in results:
        combined.update(result)
    return combined


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _strip_thinking_tokens(text: str) -> str:
    """Remove <think>…</think> blocks emitted by reasoning models (e.g. Kimi K2)."""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()


def _is_garbage_output(text: str) -> bool:
    """
    Return True if the chairman output looks like a hallucination rather than a synthesis.

    Catches common failure modes: raw HTTP requests, JSON blobs, code snippets,
    or extremely short outputs that couldn't be a real answer.
    """
    stripped = text.strip()
    if len(stripped) < 30:
        return True
    http_pattern = re.compile(
        r'^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+\S+\s+HTTP/',
        re.IGNORECASE,
    )
    if http_pattern.match(stripped):
        return True
    if stripped.startswith(('{', '[', '```', '---\n', 'Host:', 'Content-Type:')):
        return True
    return False


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Extract the ordered ranking list from a model's Stage 2 evaluation.

    Strips thinking tokens first, then looks for the 'FINAL RANKING:' section.
    Falls back to scanning the full text if the section is missing.

    Args:
        ranking_text: Raw response text from a council model's Stage 2 output

    Returns:
        Ordered list of label strings, e.g. ['Response C', 'Response A', 'Response B']
    """
    text = _strip_thinking_tokens(ranking_text)

    RANKING_HEADER = 'FINAL RANKING:'
    if RANKING_HEADER in text:
        ranking_section = text.split(RANKING_HEADER, 1)[1]
        numbered = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
        if numbered:
            return [re.search(r'Response [A-Z]', m).group() for m in numbered]
        return re.findall(r'Response [A-Z]', ranking_section)

    return re.findall(r'Response [A-Z]', text)


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str],
) -> List[Dict[str, Any]]:
    """
    Compute each council model's average rank position across all peer evaluations.

    Args:
        stage2_results: List of Stage 2 outputs, each containing a 'ranking' field
        label_to_model: Maps anonymous label ('Response A') to the actual model ID

    Returns:
        List of {model, average_rank, rankings_count} dicts, sorted best-first
    """
    model_positions: Dict[str, List[int]] = defaultdict(list)

    for ranking in stage2_results:
        parsed = parse_ranking_from_text(ranking['ranking'])
        for position, label in enumerate(parsed, start=1):
            if label in label_to_model:
                model_positions[label_to_model[label]].append(position)

    aggregate = [
        {
            'model': model,
            'average_rank': round(sum(positions) / len(positions), 2),
            'rankings_count': len(positions),
        }
        for model, positions in model_positions.items()
        if positions
    ]
    aggregate.sort(key=lambda x: x['average_rank'])
    return aggregate


# ─── Stage 1 ─────────────────────────────────────────────────────────────────

async def stage1_collect_responses(
    user_query: str,
    history: List[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Query all council models in parallel and collect their responses.

    If a council model fails, the fallback model substitutes for that slot.
    Conversation history is prepended so models can handle follow-up questions.

    Args:
        user_query: The user's current question
        history: Prior {role, content} turns for multi-turn context

    Returns:
        List of {model, response} dicts for each successful response
    """
    settings = storage.get_settings()
    council_models: List[str] = settings.get('council_models', [])
    fallback_model: Optional[str] = settings.get('fallback_model')

    messages = (history or []) + [{'role': 'user', 'content': user_query}]
    responses = await _query_mixed_models(council_models, messages, max_tokens=2048)

    stage1_results = []
    failed_count = 0

    for model, response in responses.items():
        if response is not None:
            stage1_results.append({'model': model, 'response': response.get('content', '')})
        else:
            failed_count += 1
            logger.warning('Council model failed: %s', model)

    if failed_count > 0 and fallback_model:
        logger.warning('%d council model(s) failed — using fallback (%s)', failed_count, fallback_model)
        fallback_tasks = [query_model(fallback_model, messages) for _ in range(failed_count)]
        fallback_responses = await asyncio.gather(*fallback_tasks)
        for fb in fallback_responses:
            if fb is not None:
                stage1_results.append({'model': fallback_model, 'response': fb.get('content', '')})
            else:
                logger.error('Fallback model also failed: %s', fallback_model)

    return stage1_results


# ─── Stage 2 ─────────────────────────────────────────────────────────────────

async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Ask each council model to evaluate and rank all Stage 1 responses.

    Responses are anonymised (A/B/C) to prevent bias. Each model's raw text
    and parsed ranking are returned for transparency.

    Args:
        user_query: The original user question (provides context for evaluation)
        stage1_results: Outputs from Stage 1

    Returns:
        Tuple of (stage2_results, label_to_model) where label_to_model maps
        'Response A' → actual model ID
    """
    labels = [chr(FIRST_LABEL_ASCII + i) for i in range(len(stage1_results))]
    label_to_model = {
        f'Response {label}': result['model']
        for label, result in zip(labels, stage1_results)
    }

    responses_text = '\n\n'.join([
        f'Response {label}:\n'
        f'{result["response"][:MAX_RESPONSE_CHARS]}'
        f'{"..." if len(result["response"]) > MAX_RESPONSE_CHARS else ""}'
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = build_ranking_prompt(user_query, responses_text)
    messages = [{'role': 'user', 'content': ranking_prompt}]

    settings = storage.get_settings()
    council_models: List[str] = settings.get('council_models', [])
    responses = await _query_mixed_models(council_models, messages, max_tokens=1024)

    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = response.get('content', '')
            stage2_results.append({
                'model': model,
                'ranking': full_text,
                'parsed_ranking': parse_ranking_from_text(full_text),
            })

    return stage2_results, label_to_model


# ─── Stage 3A ────────────────────────────────────────────────────────────────

async def stage3a_council_review(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    aggregate_rankings: List[Dict[str, Any]],
) -> str:
    """
    Generate a per-model critique using the independent reviewer model.

    The reviewer is distinct from all council members. Thinking tokens are
    stripped from the output before returning.

    Args:
        user_query: The original user question
        stage1_results: Individual model responses from Stage 1
        stage2_results: Peer ranking evaluations from Stage 2
        aggregate_rankings: Computed average ranks per model

    Returns:
        Markdown-formatted council review string
    """
    ranking_order = {r['model']: r['average_rank'] for r in aggregate_rankings}
    sorted_results = sorted(stage1_results, key=lambda x: ranking_order.get(x['model'], 999))

    stage1_text = '\n\n'.join([
        f'Model: {r["model"]}\nResponse: {r["response"]}' for r in sorted_results
    ])
    stage2_text = '\n\n'.join([
        f'Model: {r["model"]}\nRanking: {r["ranking"]}' for r in stage2_results
    ])

    prompt = build_council_review_prompt(user_query, stage1_text, stage2_text)

    try:
        results = await _query_mixed_models(
            [REVIEW_MODEL], [{'role': 'user', 'content': prompt}], max_tokens=2048
        )
        response = results.get(REVIEW_MODEL)
        if response:
            return _strip_thinking_tokens(response.get('content', ''))
        raise ValueError('Empty response from reviewer')
    except Exception as e:
        logger.error('Stage 3A (Council Review) failed: %s', e)
        return f'*Council review unavailable: {e}*'


# ─── Stage 3B ────────────────────────────────────────────────────────────────

async def stage3b_synthesize(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    aggregate_rankings: List[Dict[str, Any]],
) -> str:
    """
    Synthesize the final answer using the custom fine-tuned chairman model.

    Falls back to the Groq reviewer model if the HuggingFace endpoint is
    unavailable (e.g. model not yet loaded or missing pipeline_tag).

    Args:
        user_query: The original user question
        stage1_results: Individual model responses from Stage 1
        aggregate_rankings: Computed average ranks per model

    Returns:
        The final synthesized answer as a markdown string
    """
    ranking_order = {r['model']: r['average_rank'] for r in aggregate_rankings}
    sorted_results = sorted(
        stage1_results, key=lambda x: ranking_order.get(x['model'], 999)
    )

    ranked_responses = ''.join([
        f"\n\n--- Response from {r['model']} "
        f"(Rank #{i}, Score: {ranking_order.get(r['model'], '?')}) ---\n{r['response']}"
        for i, r in enumerate(sorted_results, start=1)
    ])
    synthesis_input = f'Question: {user_query}{ranked_responses}'
    prompt = build_chairman_hf_prompt(synthesis_input)

    try:
        return await _call_local_chairman(prompt)
    except Exception as e:
        logger.warning('Stage 3B (local chairman) failed: %s — trying HF', e)
    try:
        return await _call_hf_chairman(prompt)
    except Exception as e:
        logger.warning('Stage 3B (HF chairman) failed: %s — using fallback', e)
        return await _synthesis_fallback(user_query, sorted_results, ranking_order)


async def _call_local_chairman(prompt: str) -> str:
    """
    Call the local mlx-lm server.

    The server must be started separately:
        mlx_lm.server --model models/quantized --port 8002

    Raises:
        Exception: If the server is unreachable or returns an error
    """
    client = _get_chairman_client()
    response = await client.post(
        LOCAL_CHAIRMAN_URL,
        json={
            'model': LOCAL_CHAIRMAN_MODEL,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 1024,
            'temperature': 0.7,
        },
    )
    response.raise_for_status()
    content = response.json()['choices'][0]['message']['content'].strip()
    if not content:
        raise RuntimeError('Empty response from local chairman')
    if _is_garbage_output(content):
        raise RuntimeError(f'Chairman returned invalid output: {content[:120]}')
    return content


async def _call_hf_chairman(prompt: str) -> str:
    """
    Call the custom HuggingFace chairman model.

    Args:
        prompt: Alpaca-formatted prompt string

    Returns:
        Generated text string

    Raises:
        Exception: If the model returns a non-200 status or unexpected format
    """
    client = _get_chairman_client()
    response = await client.post(
        CUSTOM_CHAIRMAN_API_URL,
        headers={'Authorization': f'Bearer {HF_API_TOKEN}'},
        json={
            'inputs': prompt,
            'parameters': {
                'max_new_tokens': 1024,
                'temperature': 0.7,
                'return_full_text': False,
            },
        },
    )

    if response.status_code == 503:
        wait_time = response.json().get('estimated_time', 30)
        raise RuntimeError(f'Model loading (est. {wait_time:.0f}s) — retry shortly')

    if response.status_code != 200:
        raise RuntimeError(f'HF API error {response.status_code}: {response.text[:200]}')

    result = response.json()
    if isinstance(result, list) and result:
        generated = result[0].get('generated_text', '').strip()
        if generated:
            return generated

    raise RuntimeError(f'Unexpected HF response format: {result}')


async def _synthesis_fallback(
    user_query: str,
    sorted_results: List[Dict[str, Any]],
    ranking_order: Dict[str, float],
) -> str:
    """
    Fallback synthesis via Groq when the HuggingFace model is unavailable.

    Args:
        user_query: The original user question
        sorted_results: Council responses sorted best-first
        ranking_order: Maps model ID → average rank score

    Returns:
        Synthesized answer string, or an error message if all models fail
    """
    ranked_text = '\n\n'.join([
        f'Rank #{i} — {r["model"]} (score: {ranking_order.get(r["model"], "?")}):\n{r["response"]}'
        for i, r in enumerate(sorted_results, 1)
    ])
    prompt = build_chairman_fallback_prompt(user_query, ranked_text)

    try:
        results = await _query_mixed_models([REVIEW_MODEL], [{'role': 'user', 'content': prompt}])
        response = results.get(REVIEW_MODEL)
        if response:
            return response.get('content', '')
    except Exception as e:
        logger.error('Synthesis fallback also failed: %s', e)

    return '*Synthesis unavailable — all chairman models failed*'


# ─── Stage 3 Orchestrator ─────────────────────────────────────────────────────

async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    aggregate_rankings: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run Stage 3A (council review) and Stage 3B (synthesis) in parallel.

    Args:
        user_query: The original user question
        stage1_results: Outputs from Stage 1
        stage2_results: Outputs from Stage 2
        aggregate_rankings: Pre-computed rankings; calculated here if not provided

    Returns:
        Dict with review, review_model, synthesis, synthesis_model, model, response
    """
    if aggregate_rankings is None:
        labels = [chr(FIRST_LABEL_ASCII + i) for i in range(len(stage1_results))]
        label_to_model = {
            f'Response {label}': result['model']
            for label, result in zip(labels, stage1_results)
        }
        aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    review, synthesis = await asyncio.gather(
        stage3a_council_review(user_query, stage1_results, stage2_results, aggregate_rankings),
        stage3b_synthesize(user_query, stage1_results, aggregate_rankings),
    )

    return {
        'review': review,
        'review_model': REVIEW_MODEL,
        'synthesis': synthesis,
        'synthesis_model': 'polyllm-chairman',
        'model': f'{REVIEW_MODEL} + polyllm-chairman',
        # Kept for backward compat with stored conversations that use stage3.response
        'response': f'{review}\n\n---\n\n{synthesis}',
    }


# ─── Title Generation ─────────────────────────────────────────────────────────

async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a new conversation from its first message.

    Args:
        user_query: The first user message in the conversation

    Returns:
        A 3-5 word title string, truncated to MAX_TITLE_LENGTH characters
    """
    settings = storage.get_settings()
    council_models: List[str] = settings.get('council_models', [])
    title_model = council_models[0] if council_models else REVIEW_MODEL

    prompt = build_title_prompt(user_query)
    try:
        response = await query_model(title_model, [{'role': 'user', 'content': prompt}])
        if response:
            title = response.get('content', 'New Conversation').strip().strip('"\'')
            if len(title) > MAX_TITLE_LENGTH:
                title = title[:MAX_TITLE_LENGTH - 3] + '...'
            return title
    except Exception as e:
        logger.warning('Title generation failed: %s', e)

    return 'New Conversation'


# ─── Full Council Runner ──────────────────────────────────────────────────────

async def run_full_council(
    user_query: str,
    history: List[Dict[str, str]] = None,
) -> Tuple[List, List, Dict, Dict]:
    """
    Execute the complete 3-stage council pipeline for a single user query.

    Args:
        user_query: The user's question
        history: Prior conversation turns for multi-turn context

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    stage1_results = await stage1_collect_responses(user_query, history)

    if not stage1_results:
        return [], [], {
            'model': 'error',
            'response': 'All models failed to respond. Please try again.',
        }, {}

    stage2_results, label_to_model = await stage2_collect_rankings(user_query, stage1_results)
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    stage3_result = await stage3_synthesize_final(
        user_query, stage1_results, stage2_results, aggregate_rankings
    )

    metadata = {
        'label_to_model': label_to_model,
        'aggregate_rankings': aggregate_rankings,
    }
    return stage1_results, stage2_results, stage3_result, metadata
