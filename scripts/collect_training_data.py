#!/usr/bin/env python3
"""
Automated training data collection for the PolyLLM Chairman Model.

Reads questions from manual_questions.jsonl, sends each through the
3-stage council pipeline via the backend API, and saves results in:
  1. data/conversations/  (automatic — same as the UI)
  2. data/training/       (training-friendly format for fine-tuning)

The script is crash-safe: progress is saved after every question so you
can stop and resume at any time.

Usage:
    uv run scripts/collect_training_data.py                    # run all pending
    uv run scripts/collect_training_data.py --limit 2          # test with 2 questions
    uv run scripts/collect_training_data.py --dry-run          # preview without API calls
    uv run scripts/collect_training_data.py --retry-failed     # retry previously failed
    uv run scripts/collect_training_data.py --delay 15         # 15s between questions
"""

# ─── Imports ──────────────────────────────────────────────────────────────────

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

# ─── Config ───────────────────────────────────────────────────────────────────

API_BASE = "http://localhost:8001"
QUESTIONS_FILE = Path("manual_questions.jsonl")
TRAINING_DIR = Path("data/training")
DEFAULT_DELAY_SECONDS = 10


# ─── File I/O ─────────────────────────────────────────────────────────────────

def load_questions() -> list[dict]:
    """Load all questions from the JSONL file."""
    questions = []
    with open(QUESTIONS_FILE, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                questions.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  ⚠  Skipping malformed line {line_num}: {e}")
    return questions


def save_questions(questions: list[dict]) -> None:
    """Persist the updated question list (with status flags) back to JSONL."""
    with open(QUESTIONS_FILE, "w") as f:
        for q in questions:
            f.write(json.dumps(q) + "\n")


def save_training_example(question: dict, conversation_id: str, result: dict) -> Path:
    """
    Write a single training example to data/training/<id>.json.

    Format:
        question, council_responses (with ranks), rankings, chairman_answer
    """
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)

    example = {
        "id": question["id"],
        "domain": question.get("domain", "general"),
        "question": question["question"],
        "conversation_id": conversation_id,
        "council_responses": [],
        "rankings": [],
        "chairman_answer": "",
        "chairman_model": "",
        "aggregate_rankings": [],
        "label_to_model": {},
    }

    # Stage 1 — individual model responses
    for resp in result.get("stage1", []):
        example["council_responses"].append({
            "model": resp["model"],
            "response": resp["response"],
        })

    # Stage 2 — peer rankings
    for rank in result.get("stage2", []):
        example["rankings"].append({
            "model": rank["model"],
            "ranking_text": rank["ranking"],
            "parsed_ranking": rank.get("parsed_ranking", []),
        })

    # Stage 3 — chairman synthesis
    stage3 = result.get("stage3", {})
    example["chairman_answer"] = stage3.get("response", "")
    example["chairman_model"] = stage3.get("model", "")

    # Metadata
    metadata = result.get("metadata", {})
    example["aggregate_rankings"] = metadata.get("aggregate_rankings", [])
    example["label_to_model"] = metadata.get("label_to_model", {})

    out_path = TRAINING_DIR / f"{question['id']}.json"
    with open(out_path, "w") as f:
        json.dump(example, f, indent=2)

    return out_path


# ─── API Calls ────────────────────────────────────────────────────────────────

async def check_backend_health() -> bool:
    """Return True if the backend is running and responding."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{API_BASE}/")
            return resp.status_code == 200
    except Exception:
        return False


async def process_question(
    question: dict,
    client: httpx.AsyncClient,
) -> tuple[str, dict]:
    """
    Send one question through the full 3-stage council pipeline.

    Returns (conversation_id, api_result_dict).
    """
    # 1. Create a new conversation
    resp = await client.post(f"{API_BASE}/api/conversations", json={}, timeout=10.0)
    resp.raise_for_status()
    conversation_id = resp.json()["id"]

    # 2. Send the question — triggers Stage 1 → 2 → 3 + title generation
    #    Timeout is generous: the pipeline queries 3 models twice + chairman
    resp = await client.post(
        f"{API_BASE}/api/conversations/{conversation_id}/message",
        json={"content": question["question"]},
        timeout=300.0,
    )
    resp.raise_for_status()
    result = resp.json()

    return conversation_id, result


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect training data for the PolyLLM Chairman Model"
    )
    parser.add_argument(
        "--delay", type=int, default=DEFAULT_DELAY_SECONDS,
        help=f"Seconds to wait between questions (default: {DEFAULT_DELAY_SECONDS})",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Process at most N questions (useful for testing)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be processed, without making any API calls",
    )
    parser.add_argument(
        "--retry-failed", action="store_true",
        help="Also retry questions whose status is 'failed'",
    )
    args = parser.parse_args()

    # ── Preflight checks ─────────────────────────────────────────────────
    print("🔍 Checking backend health...")
    if not await check_backend_health():
        print("❌ Backend is not running! Start it first:")
        print("   uv run -m backend.main")
        sys.exit(1)
    print("✅ Backend is healthy\n")

    # ── Load & filter questions ──────────────────────────────────────────
    questions = load_questions()

    pending = [
        q for q in questions
        if q.get("status") not in ("done",)
        or (args.retry_failed and q.get("status") == "failed")
    ]
    # Correct filter: pending means NOT done; if retry_failed, also include failed
    pending = []
    for q in questions:
        status = q.get("status")
        if status == "done":
            continue
        if status == "failed" and not args.retry_failed:
            continue
        pending.append(q)

    done_count = sum(1 for q in questions if q.get("status") == "done")
    failed_count = sum(1 for q in questions if q.get("status") == "failed")

    print(f"📋 Total questions:    {len(questions)}")
    print(f"✅ Already completed:  {done_count}")
    print(f"❌ Previously failed:  {failed_count}")
    print(f"⏳ Pending this run:   {len(pending)}")

    if args.limit:
        pending = pending[: args.limit]
        print(f"🔒 Limited to:         {args.limit}")

    if not pending:
        print("\n🎉 Nothing to do — all questions are already processed!")
        return

    # ── Cost estimate ────────────────────────────────────────────────────
    # Per question: Stage1 (3 calls) + Stage2 (3 calls) + Stage3 (1) + Title (1) = 8
    total_calls = len(pending) * 8
    print(f"\n💰 Estimated API calls: ~{total_calls}")
    print(f"   Stage 1 (council):  {len(pending) * 3}")
    print(f"   Stage 2 (ranking):  {len(pending) * 3}")
    print(f"   Stage 3 + title:    {len(pending) * 2}")

    # ── Dry run ──────────────────────────────────────────────────────────
    if args.dry_run:
        print("\n🏃 DRY RUN — would process these questions:\n")
        for i, q in enumerate(pending, 1):
            print(f"  {i:3}. [{q['id']}] ({q.get('domain', '?'):20}) {q['question'][:60]}...")
        print(f"\n   Total: {len(pending)} questions, ~{total_calls} API calls")
        return

    # ── Process questions ────────────────────────────────────────────────
    print(f"\n{'━' * 60}")
    print(f"🚀 Starting data collection")
    print(f"   Questions: {len(pending)}  |  Delay: {args.delay}s")
    print(f"{'━' * 60}\n")

    success = 0
    failed = 0

    async with httpx.AsyncClient() as client:
        for i, question in enumerate(pending):
            qid = question["id"]
            domain = question.get("domain", "?")
            qtext = question["question"]

            print(f"[{i + 1}/{len(pending)}] {qid} ({domain})")
            print(f"  Q: {qtext[:75]}{'...' if len(qtext) > 75 else ''}")

            try:
                t0 = time.time()
                conversation_id, result = await process_question(question, client)
                elapsed = time.time() - t0

                # Save training-format data
                out_path = save_training_example(question, conversation_id, result)

                # Mark done & persist progress immediately
                question["status"] = "done"
                question["conversation_id"] = conversation_id
                # Remove any leftover error from a prior failed attempt
                question.pop("error", None)
                save_questions(questions)

                # Print summary
                s1 = len(result.get("stage1", []))
                s2 = len(result.get("stage2", []))
                chairman = result.get("stage3", {}).get("model", "?")
                ans_len = len(result.get("stage3", {}).get("response", ""))

                print(f"  ✅ Done in {elapsed:.1f}s")
                print(f"     Responses: {s1} | Rankings: {s2} | Chairman: {chairman}")
                print(f"     Answer length: {ans_len:,} chars | Saved: {out_path}")

                success += 1

            except httpx.TimeoutException:
                print(f"  ❌ TIMEOUT — pipeline took too long (>300s)")
                question["status"] = "failed"
                question["error"] = "timeout"
                save_questions(questions)
                failed += 1

            except httpx.HTTPStatusError as e:
                print(f"  ❌ HTTP ERROR {e.response.status_code}: {e.response.text[:200]}")
                question["status"] = "failed"
                question["error"] = f"http_{e.response.status_code}"
                save_questions(questions)
                failed += 1

            except Exception as e:
                print(f"  ❌ ERROR: {type(e).__name__}: {e}")
                question["status"] = "failed"
                question["error"] = str(e)
                save_questions(questions)
                failed += 1

            # Delay before the next question (skip after the last one)
            if i < len(pending) - 1:
                print(f"  ⏱  Waiting {args.delay}s before next question...\n")
                await asyncio.sleep(args.delay)

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"\n{'━' * 60}")
    print(f"📊 Collection Complete")
    print(f"   ✅ Succeeded: {success}")
    print(f"   ❌ Failed:    {failed}")
    print(f"   📁 Training data:    {TRAINING_DIR}/")
    print(f"   📁 Conversations:    data/conversations/")
    print(f"{'━' * 60}")

    if failed > 0:
        print(f"\n💡 To retry failed questions, run:")
        print(f"   uv run scripts/collect_training_data.py --retry-failed")


if __name__ == "__main__":
    asyncio.run(main())
