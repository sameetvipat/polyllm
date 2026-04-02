"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any, Tuple
from google import genai
from .openrouter import query_models_parallel, query_model
from .config import GEMINI_API_KEY, GEMINI_CHAIRMAN_MODEL
from . import storage


async def stage1_collect_responses(user_query: str) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question

    Returns:
        List of dicts with 'model' and 'response' keys
    """
    settings = storage.get_settings()
    council_models = settings.get('council_models', [])

    messages = [{"role": "user", "content": user_query}]

    # Query all models in parallel
    responses = await query_models_parallel(council_models, messages)

    # Format results
    stage1_results = []
    for model, response in responses.items():
        if response is not None:  # Only include successful responses
            stage1_results.append({
                "model": model,
                "response": response.get('content', '')
            })

    return stage1_results


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]

    settings = storage.get_settings()
    council_models = settings.get('council_models', [])

    # Get rankings from all council models in parallel
    responses = await query_models_parallel(council_models, messages)

    # Format results
    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model,
                "ranking": full_text,
                "parsed_ranking": parsed
            })

    return stage2_results, label_to_model


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response using Google Gemini API directly.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage2_results
    ])

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to deliver a structured Council Verdict in TWO parts:

**PART 1 — Council Review:**
For EACH model that responded, provide a brief but insightful assessment:
- Use the model's actual name as a heading (e.g., "### Model Name").
- **Strengths:** What did this model do well? (accuracy, depth, clarity, creativity, structure, etc.)
- **Weaknesses:** What were the flaws or gaps? (missing information, inaccuracies, verbosity, vagueness, etc.)
- Reference the peer rankings to support your assessment where relevant.
Keep each model review concise — 3 to 5 sentences per model.

**PART 2 — The Correct Answer (Chairman's Own Take):**
You are the most capable model in this council. After reviewing the council members' responses and considering their strengths and shortcomings, YOU must now independently answer the user's original question yourself.
- Do NOT merely summarize or combine the other models' answers.
- Answer the question DIRECTLY and COMPLETELY as if you are the primary respondent.
- Use your own superior knowledge and reasoning to provide the most accurate, thorough, and well-structured answer possible.
- Where other models were wrong, correct them. Where they missed details, fill in the gaps.
- This should be the definitive, authoritative, and correct answer the user can trust and rely on.

Format your response using clear markdown headings:
- Start with "## 📋 Council Review" for Part 1
- Then "## ⚖️ Chairman's Verdict" for Part 2

Deliver your verdict now:"""

    settings = storage.get_settings()
    chairman_model = settings.get('chairman_model', GEMINI_CHAIRMAN_MODEL)

    try:
        # Use Google Gemini SDK directly
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = await client.aio.models.generate_content(
            model=chairman_model,
            contents=chairman_prompt
        )

        return {
            "model": f"google/{chairman_model}",
            "response": response.text
        }

    except Exception as e:
        print(f"Error querying Gemini chairman model: {e}")
        return {
            "model": f"google/{chairman_model}",
            "response": f"Error: Unable to generate final synthesis. ({e})"
        }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            # This pattern looks for: number, period, optional space, "Response X"
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes, punctuation, or "Title:" prefix.

Question: {user_query}

Title:"""

    settings = storage.get_settings()
    chairman_model = settings.get('chairman_model', GEMINI_CHAIRMAN_MODEL)
    council_models = settings.get('council_models', [])

    try:
        # Use Google Gemini SDK directly for reliable title generation
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = await client.aio.models.generate_content(
            model=chairman_model,
            contents=title_prompt
        )

        title = response.text.strip()

        # Clean up the title - remove quotes
        title = title.strip('"\'')

        # Truncate if too long
        if len(title) > 50:
            title = title[:47] + "..."

        return title

    except Exception as e:
        print(f"Error generating title: {e}")
        # Fallback to a generic title or use one of the free models via OpenRouter
        try:
            # Fallback to the first available council model (free)
            fallback_model = council_models[0] if council_models else None
            if not fallback_model:
                return "New Conversation"
            messages = [{"role": "user", "content": title_prompt}]
            response = await query_model(fallback_model, messages, timeout=10.0)
            
            if response:
                title = response.get('content', 'New Conversation').strip()
                title = title.strip('"\'')
                if len(title) > 50:
                    title = title[:47] + "..."
                return title
        except Exception as e2:
            print(f"Fallback title generation failed: {e2}")
            
        return "New Conversation"


async def run_full_council(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage council process.

    Args:
        user_query: The user's question

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query)

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }, {}

    # Stage 2: Collect rankings
    stage2_results, label_to_model = await stage2_collect_rankings(user_query, stage1_results)

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize final answer
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results
    )

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings
    }

    return stage1_results, stage2_results, stage3_result, metadata
