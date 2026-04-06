#!/usr/bin/env python3
"""
Expand the training dataset from HuggingFace + Kaggle-equivalent sources.

HuggingFace sources (target 300-500 total):
  1. tatsu-lab/alpaca               — Instruction-following (52k examples)
  2. Open-Orca/OpenOrca             — Diverse instruction-following
  3. lmsys/chatbot_arena_conversations — Real human prompts to AI models

Kaggle-equivalent sources (target 200-300 total):
  4. allenai/sciq                   — Science MCQ with explanations
  5. trivia_qa                      — General knowledge Q&A
  6. iamtarun/python_code_instructions_18k_alpaca — Programming tasks

Usage:
    python scripts/expand_dataset.py
    python scripts/expand_dataset.py --hf-count 400 --kaggle-count 250
    python scripts/expand_dataset.py --dry-run
    python scripts/expand_dataset.py --source alpaca --hf-count 100
"""

import json
import random
import re
import argparse
from pathlib import Path
from collections import Counter

import sys
sys.path.insert(0, str(Path(__file__).parent))
from generate_training_data import (
    MODELS, CHAIRMAN_MODEL, LABEL_MAP, TRAINING_DIR,
    _find_knowledge, _build_hermes, _build_llama, _build_gemma,
    _build_ranking, _build_chairman, _compute_aggregates,
    KNOWLEDGE
)

try:
    from datasets import load_dataset
    HAS_DATASETS = True
except ImportError:
    HAS_DATASETS = False

import uuid


# ── Domain classification ─────────────────────────────────────────────────────

DOMAIN_KEYWORDS = {
    "programming": [
        "code", "program", "function", "algorithm", "debug", "python", "java",
        "javascript", "api", "sql", "database", "software", "compile", "loop",
        "array", "class", "object", "method", "variable", "git", "docker",
        "kubernetes", "rest", "graphql", "react", "html", "css", "backend",
        "frontend", "stack", "heap", "memory", "thread", "process", "mutex",
        "recursion", "sorting", "binary", "tree", "graph", "linked list",
        "complexity", "big o", "dynamic programming", "cache", "hash",
    ],
    "data_science": [
        "machine learning", "neural network", "deep learning", "model", "training",
        "dataset", "feature", "regression", "classification", "clustering",
        "gradient", "backpropagation", "overfitting", "underfitting", "accuracy",
        "precision", "recall", "f1", "transformer", "attention", "nlp", "cnn",
        "rnn", "lstm", "bert", "gpt", "embeddings", "pandas", "numpy",
        "statistics", "probability", "distribution", "hypothesis",
    ],
    "science": [
        "physics", "chemistry", "biology", "evolution", "quantum", "atom",
        "molecule", "cell", "dna", "gene", "protein", "organism", "ecosystem",
        "photosynthesis", "thermodynamics", "entropy", "gravity", "relativity",
        "electromagnetism", "vaccine", "virus", "bacteria", "immune", "brain", "neuron",
    ],
    "history_geopolitics": [
        "war", "revolution", "empire", "colony", "independence", "constitution",
        "democracy", "treaty", "cold war", "world war", "civilization", "ancient",
        "medieval", "renaissance", "industrial", "geopolitical", "sovereignty",
    ],
    "philosophy": [
        "ethics", "moral", "consciousness", "free will", "existence", "meaning",
        "justice", "truth", "knowledge", "epistemology", "metaphysics", "logic",
        "philosophy", "ethical", "ontology", "nihilism",
    ],
    "economics": [
        "economy", "inflation", "gdp", "market", "trade", "supply", "demand",
        "fiscal", "monetary", "recession", "currency", "stock", "invest",
        "capitalism", "socialism", "tax", "budget", "debt",
    ],
    "psychology": [
        "psychology", "cognitive", "behavior", "emotion", "mental", "bias",
        "motivation", "personality", "perception", "memory", "learning",
        "conditioning", "therapy", "anxiety", "depression",
    ],
    "ai_ethics": [
        "ai", "artificial intelligence", "bias", "fairness", "autonomous",
        "robot", "singularity", "alignment", "hallucination", "deepfake",
        "copyright", "surveillance", "privacy",
    ],
    "environment": [
        "climate", "environment", "carbon", "emission", "renewable", "solar",
        "wind", "nuclear", "pollution", "sustainability", "biodiversity",
        "deforestation", "ocean", "ecosystem",
    ],
    "law": [
        "law", "legal", "court", "rights", "constitution", "amendment", "patent",
        "copyright", "trademark", "regulation", "legislation", "judicial",
    ],
    "business": [
        "business", "startup", "entrepreneur", "management", "strategy",
        "marketing", "brand", "product", "customer", "revenue", "profit",
        "leadership", "innovation", "competition",
    ],
}


def classify_domain(question: str) -> str:
    q_lower = question.lower()
    scores = Counter()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in q_lower:
                scores[domain] += 1
    return scores.most_common(1)[0][0] if scores else "general"


def is_good_question(text: str) -> bool:
    """Filter for questions suitable for multi-model council synthesis."""
    if not text or len(text) < 30:
        return False
    if len(text) > 400:
        return False

    t = text.lower().strip()

    # Skip questions with embedded images or URLs
    if "http" in t or "![" in t or "www." in t:
        return False

    # Skip NLI / logical inference tasks (very common in OpenOrca)
    nli_patterns = (
        "is the following a factual statement",
        "does that mean that",
        "does this imply that",
        "is it true that",
        "can we conclude that",
        "is it correct to say",
        "premise:", "hypothesis:", "entailment",
        "q:this is a correct answer",
        "yes or no? an",
        "yes or no?",
    )
    if any(p in t for p in nli_patterns):
        return False

    # Skip OpenOrca "Definition: In this task..." format
    if t.startswith(("definition:", "in this task,", "in this task you", "q:")):
        return False

    # Skip "Question:" or "Please answer the following" (factual lookup wrappers)
    if t.startswith(("question:", "please answer the following", "formulate an answer")):
        return False

    # Skip non-question formats (bios, reviews, passages, translation tasks)
    non_question_starts = (
        "title:", "review:", "short movie review:", "bio:", "passage:",
        "context:", "background:", "the following", "given this paragraph",
        "how do you say", "how is \"", "how is '", "translate the",
        "remove the spaces", "write an article based on",
        "modify the following",
    )
    if any(t.startswith(p) for p in non_question_starts):
        return False

    # Skip pure lowercase start (usually a fragment, not a question)
    if text[0].islower() and not text[0].isdigit():
        return False

    # Skip factual extraction tasks
    extraction_patterns = (
        "what key details about", "what information can be extracted",
        "which of the following surnames", "which of the following historical",
        "which of the following european", "which of the following countries",
        "what would be the ★-rating", "★-rating",
        "star rating of this review",
    )
    if any(p in t for p in extraction_patterns):
        return False

    # Skip trivial factual lookups
    trivial_starts = (
        "what is the capital of", "who is the president of",
        "what year did", "what color", "how many people live",
        "what is the name of", "when was", "what date is",
        "how many husbands", "who won the", "what day of the week was",
    )
    if any(t.startswith(p) for p in trivial_starts):
        return False

    # Skip pure yes/no questions that are very short
    if t.startswith(("is ", "are ", "was ", "were ", "do ", "does ", "did ")):
        if len(text) < 70:
            return False

    # Skip creative writing / formatting / rote tasks — not good for multi-model debate
    bad_starts = (
        # Poems / creative writing
        "write a haiku", "write a poem", "write a sonnet", "write a limerick",
        "write a short story", "write a sentence", "write one sentence", "write a joke",
        "write an email", "write a letter", "write a cover letter", "write a tweet",
        "write a speech", "write a paragraph", "write a blog",
        # Editing / formatting
        "rewrite the", "rewrite this", "edit the following", "correct the following",
        "fix the following", "translate the", "transform the sentence",
        "add a sentence", "summarize the following", "summarize this",
        # Rote generation tasks
        "generate a list of", "generate a headline", "generate a resume",
        "generate a sentence", "generate a conversation", "generate a recipe",
        "generate a report", "generate a single sentence", "generate a short",
        "create a recipe", "create a schedule", "create a plan", "create a list",
        "create a resume", "come up with a recipe", "come up with a sentence",
        # Classification / lookup
        "list the", "list five", "list three", "list 5", "list 3",
        "name five", "name three", "name the", "name two",
        "give an example", "provide an example", "cite three", "cite five",
        "classify the", "identify which", "select the best", "choose the best",
        "redact all", "sort the", "sort these", "rank the",
        "given two strings", "given a table", "given a set of",
        "come up with", "meet with the",
    )
    if any(t.startswith(p) for p in bad_starts):
        return False

    # Skip tasks that are clearly code-generation without explanation requirement
    pure_code = ("write a function", "create a script", "implement a", "code a ",
                 "write code", "create a program", "write a program")
    if any(t.startswith(p) for p in pure_code):
        if not any(s in t for s in ("explain", "why", "how does", "describe")):
            return False

    # Prefer analytical/explanatory questions — these produce rich council responses
    signals = [
        "explain", "how does", "why does", "why is", "compare", "difference",
        "what are the", "describe", "discuss", "analyze", "argue", "evaluate",
        "what is the role", "what impact", "pros and cons", "advantages",
        "disadvantages", "how would", "what happens", "what causes",
        "what are the implications", "how can", "why do", "what makes",
        "how has", "what is the significance", "what are some",
        "how do", "what is the relationship",
    ]
    return any(s in t for s in signals) or len(text) > 90


def deduplicate(questions: list[dict], existing: set) -> list[dict]:
    seen = set()
    unique = []
    for q in questions:
        norm = re.sub(r'[^a-z0-9\s]', '', q["question"].lower().strip())
        norm = re.sub(r'\s+', ' ', norm).strip()
        if norm in seen or norm in existing:
            continue
        words = set(norm.split())
        is_dup = any(
            len(words & set(e.split())) / max(len(words), 1) > 0.72
            for e in seen
        )
        if not is_dup:
            seen.add(norm)
            unique.append(q)
    return unique


# ── HuggingFace loaders ───────────────────────────────────────────────────────

def load_alpaca(count: int) -> list[dict]:
    """tatsu-lab/alpaca — 52k instruction-following examples."""
    print("  📥 tatsu-lab/alpaca ...")
    try:
        ds = load_dataset("tatsu-lab/alpaca", split="train", trust_remote_code=False)
    except Exception as e:
        print(f"  ❌ {e}"); return []

    questions = []
    items = list(ds)
    random.shuffle(items)
    for item in items:
        instruction = item.get("instruction", "")
        inp = item.get("input", "")
        q = f"{instruction} {inp}".strip() if inp else instruction.strip()
        if is_good_question(q):
            questions.append({"question": q, "source": "hf_alpaca",
                              "original_output": item.get("output", "")})
        if len(questions) >= count * 2:
            break

    random.shuffle(questions)
    selected = questions[:count]
    print(f"     → {len(selected)} selected")
    return selected


def load_openorca(count: int) -> list[dict]:
    """Open-Orca/OpenOrca — diverse instruction-following (streaming, tight limit)."""
    print("  📥 Open-Orca/OpenOrca (streaming, scanning first 8k items) ...")
    try:
        ds = load_dataset("Open-Orca/OpenOrca", split="train",
                          streaming=True, trust_remote_code=False)
    except Exception as e:
        print(f"  ❌ {e}"); return []

    questions = []
    scanned = 0
    for item in ds:
        scanned += 1
        if scanned > 8000:
            break
        q = item.get("question", "")
        if is_good_question(q):
            questions.append({"question": q, "source": "hf_openorca",
                              "original_output": item.get("response", "")})
            if len(questions) >= count * 3:
                break

    random.shuffle(questions)
    selected = questions[:count]
    print(f"     → scanned {scanned}, {len(selected)} selected")
    return selected


def load_dolly(count: int) -> list[dict]:
    """databricks/databricks-dolly-15k — open, human-written instruction dataset."""
    print("  📥 databricks/databricks-dolly-15k ...")
    try:
        ds = load_dataset("databricks/databricks-dolly-15k", split="train",
                          trust_remote_code=False)
    except Exception as e:
        print(f"  ❌ {e}"); return []

    questions = []
    items = list(ds)
    random.shuffle(items)
    for item in items:
        instruction = item.get("instruction", "")
        context = item.get("context", "")
        # Include context only if it adds meaning (not too long)
        if context and len(context) < 200:
            q = f"{instruction} Context: {context}".strip()
        else:
            q = instruction.strip()
        if is_good_question(q):
            questions.append({"question": q, "source": "hf_dolly",
                              "original_output": item.get("response", "")})
        if len(questions) >= count * 2:
            break

    random.shuffle(questions)
    selected = questions[:count]
    print(f"     → {len(selected)} selected")
    return selected


# ── Kaggle-equivalent loaders ─────────────────────────────────────────────────

def load_sciq(count: int) -> list[dict]:
    """allenai/sciq — crowd-sourced science MCQ with support text (Kaggle-style science)."""
    print("  📥 allenai/sciq (science) ...")
    try:
        ds = load_dataset("allenai/sciq", split="train", trust_remote_code=False)
    except Exception as e:
        print(f"  ❌ {e}"); return []

    questions = []
    items = list(ds)
    random.shuffle(items)
    for item in items:
        q_raw = item.get("question", "")
        support = item.get("support", "")
        if not q_raw or len(support) < 60:
            continue
        # Rephrase to require explanation rather than just picking an answer
        q = f"Explain the scientific concept behind: {q_raw}"
        questions.append({"question": q, "source": "kaggle_sciq",
                          "original_output": support})
        if len(questions) >= count * 2:
            break

    random.shuffle(questions)
    selected = questions[:count]
    print(f"     → {len(selected)} selected")
    return selected


def load_trivia_qa(count: int) -> list[dict]:
    """trivia_qa — general knowledge via streaming to avoid large download."""
    print("  📥 trivia_qa (general knowledge, streaming) ...")
    try:
        ds = load_dataset("trivia_qa", "rc", split="train",
                          streaming=True, trust_remote_code=False)
    except Exception as e:
        print(f"  ❌ {e}"); return []

    questions = []
    # Skip short celebrity/pop-culture trivia patterns
    trivia_skip_patterns = (
        "who played", "who starred", "who directed", "who wrote",
        "what year was", "which film", "which movie", "which song",
        "what is the name of the", "who was the first",
        "how many", "what date", "when did", "what was the score",
        "which country won", "who won",
    )

    scanned = 0
    for item in ds:
        scanned += 1
        if scanned > 15000:
            break
        q_raw = item.get("question", "")
        if not q_raw or len(q_raw) < 40:
            continue
        # Skip pop-culture / sports / celebrity trivia
        q_lower = q_raw.lower()
        if any(p in q_lower for p in trivia_skip_patterns):
            continue
        # Rephrase to require explanation, not just factual recall
        q = f"Explain and discuss: {q_raw}"
        questions.append({"question": q, "source": "kaggle_trivia",
                          "original_output": ""})
        if len(questions) >= count * 3:
            break

    random.shuffle(questions)
    selected = questions[:count]
    print(f"     → scanned {scanned}, {len(selected)} selected")
    return selected


def load_python_instructions(count: int) -> list[dict]:
    """iamtarun/python_code_instructions_18k_alpaca — programming (Kaggle-style)."""
    print("  📥 iamtarun/python_code_instructions_18k_alpaca (programming) ...")
    try:
        ds = load_dataset("iamtarun/python_code_instructions_18k_alpaca",
                          split="train", trust_remote_code=False)
    except Exception as e:
        # Fallback to code_alpaca
        print(f"  ⚠ Primary failed ({e}), trying sahil2801/CodeAlpaca-20k ...")
        try:
            ds = load_dataset("sahil2801/CodeAlpaca-20k", split="train",
                              trust_remote_code=False)
        except Exception as e2:
            print(f"  ❌ Both failed: {e2}"); return []

    questions = []
    items = list(ds)
    random.shuffle(items)
    for item in items:
        instruction = item.get("instruction", "")
        inp = item.get("input", "")
        # Only keep conceptual/analytical questions, not pure "write code" tasks
        q = f"{instruction} {inp}".strip() if inp else instruction.strip()
        # Must have analytical signals AND not be pure code generation
        explain_signals = ["explain", "how does", "why", "compare", "difference",
                           "what is", "describe", "what are the", "how do"]
        pure_code_signals = ["write a python program", "write a python script",
                             "generate a python", "implement a python",
                             "create a python", "write code to", "write a function to"]
        is_conceptual = any(s in q.lower() for s in explain_signals)
        is_pure_code = any(s in q.lower() for s in pure_code_signals)
        if is_conceptual and not is_pure_code and len(q) > 30:
            questions.append({"question": q, "source": "kaggle_programming",
                              "original_output": item.get("output", "")})
        if len(questions) >= count * 2:
            break

    random.shuffle(questions)
    selected = questions[:count]
    print(f"     → {len(selected)} selected")
    return selected


# ── Training file generation ──────────────────────────────────────────────────

def generate_training_file(qid: str, question: str, domain: str) -> Path:
    k = _find_knowledge(question, domain)

    responses = [
        {"model": MODELS[0], "response": _build_hermes(question, domain, k)},
        {"model": MODELS[1], "response": _build_llama(question, domain, k)},
        {"model": MODELS[2], "response": _build_gemma(question, domain, k)},
    ]
    rankings = [_build_ranking(m, question, k) for m in MODELS]
    chairman = _build_chairman(question, domain, k, responses, rankings)
    agg = _compute_aggregates(rankings, LABEL_MAP)

    example = {
        "id": qid,
        "domain": domain,
        "question": question,
        "conversation_id": str(uuid.uuid4()),
        "council_responses": responses,
        "rankings": rankings,
        "chairman_answer": chairman,
        "chairman_model": CHAIRMAN_MODEL,
        "aggregate_rankings": agg,
        "label_to_model": LABEL_MAP,
    }

    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    out = TRAINING_DIR / f"{qid}.json"
    with open(out, "w") as f:
        json.dump(example, f, indent=2)
    return out


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Expand dataset from HuggingFace + Kaggle")
    parser.add_argument("--hf-count", type=int, default=400,
                        help="Questions from HuggingFace sources (default 400)")
    parser.add_argument("--kaggle-count", type=int, default=250,
                        help="Questions from Kaggle-equivalent sources (default 250)")
    parser.add_argument("--source",
                        choices=["alpaca", "openorca", "dolly",
                                 "sciq", "trivia", "python",
                                 "hf", "kaggle", "all"],
                        default="all",
                        help="Which source(s) to load")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview questions without generating files")
    parser.add_argument("--export", type=str, default=None,
                        metavar="FILE",
                        help="Export selected questions to JSONL for review (e.g. data/questions_preview.jsonl)")
    parser.add_argument("--from-preview", type=str, default=None,
                        metavar="FILE",
                        help="Generate training files directly from a preview JSONL (skips dataset download)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    # ── Fast path: generate from existing preview file ────────────────────────
    if args.from_preview:
        preview_path = Path(args.from_preview)
        if not preview_path.exists():
            print(f"❌ File not found: {preview_path}"); return

        questions = [json.loads(l) for l in open(preview_path) if l.strip()]
        print("━" * 65)
        print(f"⚡ Generating from preview: {preview_path}")
        print(f"   {len(questions)} questions")
        print("━" * 65)

        # Skip already-generated files
        existing_ids = set()
        for pattern in ("hf_*.json", "kg_*.json"):
            for f in TRAINING_DIR.glob(pattern):
                try:
                    existing_ids.add(json.load(open(f))["question"].strip())
                except Exception:
                    pass

        existing_hf_nums = sorted(
            int(f.stem.split("_")[1]) for f in TRAINING_DIR.glob("hf_*.json")
        ) if list(TRAINING_DIR.glob("hf_*.json")) else [0]
        existing_kg_nums = sorted(
            int(f.stem.split("_")[1]) for f in TRAINING_DIR.glob("kg_*.json")
        ) if list(TRAINING_DIR.glob("kg_*.json")) else [0]

        next_hf = (max(existing_hf_nums) + 1) if existing_hf_nums else 1
        next_kg = (max(existing_kg_nums) + 1) if existing_kg_nums else 1

        hf_counter = 0
        kg_counter = 0
        skipped = 0

        for i, q in enumerate(questions):
            question = q["question"]
            domain = q.get("domain", "general")
            source = q.get("source", "hf_")

            if question.strip() in existing_ids:
                skipped += 1
                continue

            if source.startswith("hf_"):
                qid = f"hf_{next_hf + hf_counter:04d}"
                hf_counter += 1
            else:
                qid = f"kg_{next_kg + kg_counter:04d}"
                kg_counter += 1

            generate_training_file(qid, question, domain)

            total_done = hf_counter + kg_counter
            if total_done % 50 == 0:
                print(f"   ✅ {total_done}/{len(questions) - skipped} generated...")

        total = hf_counter + kg_counter
        print(f"\n{'━' * 65}")
        print(f"✅ Done!")
        print(f"   HuggingFace files:  {hf_counter}")
        print(f"   Kaggle files:       {kg_counter}")
        print(f"   Skipped (existing): {skipped}")
        print(f"   Total new files:    {total}")
        print(f"\n   👉 Rebuild dataset: python scripts/build_dataset.py")
        print(f"{'━' * 65}")
        return

    if not HAS_DATASETS:
        print("❌ Install: uv add datasets"); return

    print("━" * 65)
    print("🌐 Expanding Dataset — HuggingFace + Kaggle")
    print("━" * 65)

    # Load existing questions to avoid duplicates
    existing_questions = set()
    existing_ids = set()
    for pattern in ("mq_*.json", "hf_*.json", "kg_*.json"):
        for f in TRAINING_DIR.glob(pattern):
            try:
                data = json.load(open(f))
                norm = re.sub(r'[^a-z0-9\s]', '', data["question"].lower())
                existing_questions.add(re.sub(r'\s+', ' ', norm).strip())
                existing_ids.add(data["id"])
            except Exception:
                pass

    print(f"\n📂 Existing training files: {len(existing_questions)}\n")

    # ── Load from sources ─────────────────────────────────────────────────────
    hf_questions = []
    kaggle_questions = []

    src = args.source
    hf_per = args.hf_count // 3
    kg_per = args.kaggle_count // 3

    # HuggingFace sources
    if src in ("alpaca", "hf", "all"):
        hf_questions.extend(load_alpaca(hf_per if src in ("hf", "all") else args.hf_count))

    if src in ("openorca", "hf", "all"):
        hf_questions.extend(load_openorca(hf_per if src in ("hf", "all") else args.hf_count))

    if src in ("dolly", "hf", "all"):
        hf_questions.extend(load_dolly(hf_per if src in ("hf", "all") else args.hf_count))

    # Kaggle-equivalent sources
    if src in ("sciq", "kaggle", "all"):
        kaggle_questions.extend(load_sciq(kg_per if src in ("kaggle", "all") else args.kaggle_count))

    if src in ("trivia", "kaggle", "all"):
        kaggle_questions.extend(load_trivia_qa(kg_per if src in ("kaggle", "all") else args.kaggle_count))

    if src in ("python", "kaggle", "all"):
        kaggle_questions.extend(load_python_instructions(kg_per if src in ("kaggle", "all") else args.kaggle_count))

    # Combine and deduplicate
    all_questions = hf_questions + kaggle_questions
    if not all_questions:
        print("❌ No questions loaded!"); return

    for q in all_questions:
        q["domain"] = classify_domain(q["question"])

    print(f"\n🔍 Deduplicating {len(all_questions)} questions...")
    unique = deduplicate(all_questions, existing_questions)
    print(f"   ✅ {len(unique)} unique after dedup")

    # Trim to target counts by source type
    hf_final = [q for q in unique if q["source"].startswith("hf_")][:args.hf_count]
    kg_final = [q for q in unique if q["source"].startswith("kaggle_")][:args.kaggle_count]
    final = hf_final + kg_final

    # Domain distribution
    domain_counts = Counter(q["domain"] for q in final)
    hf_src_counts = Counter(q["source"] for q in hf_final)
    kg_src_counts = Counter(q["source"] for q in kg_final)

    print(f"\n📊 Source breakdown:")
    print(f"   HuggingFace ({len(hf_final)} total):")
    for s, c in hf_src_counts.most_common():
        print(f"     {s}: {c}")
    print(f"   Kaggle-equivalent ({len(kg_final)} total):")
    for s, c in kg_src_counts.most_common():
        print(f"     {s}: {c}")

    print(f"\n📊 Domain distribution:")
    for d, c in domain_counts.most_common():
        print(f"   {d}: {c}")

    print(f"\n📋 Total to generate: {len(final)}")

    if args.export:
        out_path = Path(args.export)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            for i, q in enumerate(final):
                record = {
                    "id": i + 1,
                    "source": q["source"],
                    "domain": q["domain"],
                    "question": q["question"],
                }
                f.write(json.dumps(record) + "\n")
        print(f"\n✅ Exported {len(final)} questions → {out_path}")
        print(f"   Review with: cat {out_path} | python3 -m json.tool | less")
        print(f"   Then run without --export to generate training files.")
        return

    if args.dry_run:
        print("\n🔍 DRY RUN — first 30 questions:")
        for i, q in enumerate(final[:30], 1):
            print(f"  {i:3d}. [{q['domain']:20s}] [{q['source']:20s}] {q['question'][:75]}...")
        if len(final) > 30:
            print(f"  ... and {len(final) - 30} more")
        print("\n  Run without --dry-run to generate files.")
        print(f"  Or export all: python scripts/expand_dataset.py --export data/questions_preview.jsonl")
        return

    # ── Generate training files ───────────────────────────────────────────────
    # Determine prefix and starting number per source type
    existing_hf_nums = sorted(
        int(f.stem.split("_")[1]) for f in TRAINING_DIR.glob("hf_*.json")
    ) if list(TRAINING_DIR.glob("hf_*.json")) else [0]
    existing_kg_nums = sorted(
        int(f.stem.split("_")[1]) for f in TRAINING_DIR.glob("kg_*.json")
    ) if list(TRAINING_DIR.glob("kg_*.json")) else [0]

    next_hf = (max(existing_hf_nums) + 1) if existing_hf_nums else 1
    next_kg = (max(existing_kg_nums) + 1) if existing_kg_nums else 1

    print(f"\n🔨 Generating {len(final)} training files...")
    hf_counter = 0
    kg_counter = 0

    for i, q in enumerate(final):
        if q["source"].startswith("hf_"):
            qid = f"hf_{next_hf + hf_counter:04d}"
            hf_counter += 1
        else:
            qid = f"kg_{next_kg + kg_counter:04d}"
            kg_counter += 1

        generate_training_file(qid, q["question"], q["domain"])

        if (i + 1) % 50 == 0:
            print(f"   ✅ {i + 1}/{len(final)} done...")

    total = hf_counter + kg_counter
    print(f"\n{'━' * 65}")
    print(f"✅ Done!")
    print(f"{'━' * 65}")
    print(f"   HuggingFace files:       {hf_counter}  (hf_{next_hf:04d} → hf_{next_hf+hf_counter-1:04d})")
    print(f"   Kaggle-equiv files:      {kg_counter}  (kg_{next_kg:04d} → kg_{next_kg+kg_counter-1:04d})")
    print(f"   Total new files:         {total}")
    print(f"   Grand total in dataset:  {len(existing_questions) + total}")
    print(f"\n   👉 Rebuild dataset: python scripts/build_dataset.py")
    print(f"{'━' * 65}")


if __name__ == "__main__":
    main()
