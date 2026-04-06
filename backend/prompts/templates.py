"""All prompt templates for the LLM Council pipeline.

No business logic lives here — only the text that gets sent to models.
"""

# ─── Stage 2 — Ranking Prompt ─────────────────────────────────────────────────

def build_ranking_prompt(user_query: str, responses_text: str) -> str:
    """
    Build the Stage 2 prompt asking a council model to evaluate and rank
    the anonymized Stage 1 responses.

    Args:
        user_query: The original user question
        responses_text: Pre-formatted string of anonymized responses (A/B/C)

    Returns:
        Full prompt string ready to send to the model
    """
    return f"""You are evaluating different responses to the following question:

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


# ─── Stage 3A — Council Review Prompt ────────────────────────────────────────

def build_council_review_prompt(
    user_query: str,
    stage1_text: str,
    stage2_text: str,
) -> str:
    """
    Build the Stage 3A prompt asking the reviewer model to write a
    per-model critique based on peer rankings.

    Args:
        user_query: The original user question
        stage1_text: Formatted string of council responses (sorted best to worst)
        stage2_text: Formatted string of peer ranking evaluations

    Returns:
        Full prompt string ready to send to the reviewer model
    """
    return f"""You are the Chairman of an LLM Council reviewing your council members' responses.

Original Question: {user_query}

COUNCIL RESPONSES (sorted best to worst by peer rankings):
{stage1_text}

PEER RANKINGS:
{stage2_text}

Your task: Write a "## Council Review" that briefly assesses EACH model that responded.
For each model, use its actual name as a heading (e.g., "### Model Name") and note:
- **Strengths:** What it did well (accuracy, depth, clarity, structure)
- **Weaknesses:** What it missed or got wrong
- Reference the peer rankings to support your assessment.
Keep each model review to 3-5 sentences. Start your response with "## Council Review"."""


# ─── Stage 3B — Chairman Synthesis Prompt ────────────────────────────────────

CHAIRMAN_SYSTEM_INSTRUCTION = (
    'You are the Chairman of an AI Council. You are given a user\'s question and responses '
    'from multiple AI models, ranked by quality. Your task is to synthesize the most accurate, '
    'comprehensive, and well-structured answer possible. Use the best parts of the top-ranked '
    'responses, correct any errors, and fill in gaps with your own knowledge.'
)


def build_chairman_hf_prompt(synthesis_input: str) -> str:
    """
    Build the Alpaca-style prompt for the custom HuggingFace chairman model.

    The format matches the fine-tuning training format exactly.

    Args:
        synthesis_input: Pre-formatted question + ranked council responses

    Returns:
        Full Alpaca-style prompt string
    """
    return (
        'Below is an instruction that describes a task, paired with an input that provides '
        'further context. Write a response that appropriately completes the request.\n\n'
        f'### Instruction:\n{CHAIRMAN_SYSTEM_INSTRUCTION}\n\n'
        f'### Input:\n{synthesis_input}\n\n'
        '### Response:\n'
    )


def build_chairman_fallback_prompt(user_query: str, ranked_text: str) -> str:
    """
    Build the fallback synthesis prompt used when the HuggingFace model is unavailable.

    Args:
        user_query: The original user question
        ranked_text: Pre-formatted string of council responses sorted by rank

    Returns:
        Full prompt string ready to send to the fallback model
    """
    return f"""You are the Chairman of an AI Council. Based on the peer-ranked responses below, provide the definitive final answer to the user's question.

Question: {user_query}

Council Responses (best to worst by peer ranking):
{ranked_text}

Answer directly and authoritatively. Correct any errors from council members. Do NOT merely summarize — answer as the primary expert. Start with "## Chairman's Verdict"."""


# ─── Title Generation Prompt ──────────────────────────────────────────────────

def build_title_prompt(user_query: str) -> str:
    """
    Build the prompt for generating a short conversation title.

    Args:
        user_query: The first user message in the conversation

    Returns:
        Prompt string that asks for a 3-5 word title
    """
    return (
        f'Generate a very short title (3-5 words maximum) that summarizes the following question.\n'
        f'The title should be concise and descriptive. Do not use quotes, punctuation, or "Title:" prefix.\n\n'
        f'Question: {user_query}\n\n'
        f'Title:'
    )
