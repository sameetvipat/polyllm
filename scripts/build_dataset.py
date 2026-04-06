#!/usr/bin/env python3
"""
Build fine-tuning datasets from the training JSON files.

Produces multiple formats:
  1. instruction_dataset.jsonl  — Alpaca-style instruction tuning (for LoRA)
  2. chat_dataset.jsonl         — ChatML / conversation format (for chat models)
  3. dataset_stats.json         — Statistics about the dataset
  4. train.jsonl / val.jsonl / test.jsonl — 80/10/10 splits

Usage:
    python scripts/build_dataset.py
    python scripts/build_dataset.py --split-ratio 0.8 0.1 0.1
    python scripts/build_dataset.py --output-dir data/dataset
"""

import json
import argparse
import random
import hashlib
from pathlib import Path
from collections import Counter

TRAINING_DIR = Path("data/training")
OUTPUT_DIR = Path("data/dataset")

SYSTEM_PROMPT = (
    "You are the Chairman of an AI Council. You are given a user's question "
    "and responses from multiple AI models, ranked by quality. Your task is to "
    "synthesize the most accurate, comprehensive, and well-structured answer "
    "possible. Use the best parts of the top-ranked responses, correct any "
    "errors, and fill in gaps with your own knowledge."
)


def load_training_files() -> list[dict]:
    """Load all training files (mq_* manual + hf_* HuggingFace + kg_* Kaggle)."""
    files = (sorted(TRAINING_DIR.glob("mq_*.json"))
             + sorted(TRAINING_DIR.glob("hf_*.json"))
             + sorted(TRAINING_DIR.glob("kg_*.json")))
    entries = []
    skipped = 0

    for f in files:
        try:
            data = json.load(open(f))

            # Validate required fields
            if not data.get("question"):
                print(f"  ⚠ {f.name}: missing question, skipping")
                skipped += 1
                continue

            if not data.get("council_responses") or len(data["council_responses"]) < 2:
                print(f"  ⚠ {f.name}: insufficient council responses, skipping")
                skipped += 1
                continue

            chairman = data.get("chairman_answer", "")
            if not chairman or chairman.startswith("Error:") or len(chairman) < 100:
                print(f"  ⚠ {f.name}: invalid chairman answer, skipping")
                skipped += 1
                continue

            entries.append(data)
        except Exception as e:
            print(f"  ❌ {f.name}: {e}")
            skipped += 1

    print(f"\n  📂 Loaded {len(entries)} valid entries, skipped {skipped}")
    return entries


def sort_responses_by_rank(data: dict) -> list[dict]:
    """Sort council responses by their aggregate ranking (best first)."""
    responses = data.get("council_responses", [])
    aggregate = data.get("aggregate_rankings", [])

    # Build model -> rank mapping
    rank_map = {}
    for agg in aggregate:
        rank_map[agg["model"]] = agg["average_rank"]

    # Sort responses by rank (lowest average_rank = best)
    sorted_responses = sorted(
        responses,
        key=lambda r: rank_map.get(r["model"], 99)
    )

    # Attach rank info
    for resp in sorted_responses:
        resp["_rank"] = rank_map.get(resp["model"], 99)

    return sorted_responses


def build_instruction_input(question: str, sorted_responses: list[dict]) -> str:
    """Build the input field for instruction-tuning format."""
    parts = [f"Question: {question}\n"]

    for i, resp in enumerate(sorted_responses, 1):
        model_name = resp["model"].split("/")[-1]  # Short name
        rank = resp.get("_rank", i)
        parts.append(
            f"--- Response from {model_name} (Rank #{i}, "
            f"Score: {rank:.2f}) ---\n{resp['response']}\n"
        )

    return "\n".join(parts)


def build_chat_messages(question: str, sorted_responses: list[dict],
                        chairman_answer: str) -> list[dict]:
    """Build ChatML-style messages for conversation format."""
    input_text = build_instruction_input(question, sorted_responses)

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": input_text},
        {"role": "assistant", "content": chairman_answer},
    ]


def extract_chairman_verdict(chairman_answer: str) -> str:
    """Extract just the Chairman's Verdict section if present."""
    # The chairman answer has two sections:
    # 1. Council Review (per-model analysis)
    # 2. Chairman's Verdict (the actual synthesis)
    # For training, we want the FULL answer (both sections)
    return chairman_answer


def build_dataset(entries: list[dict]) -> tuple[list[dict], list[dict]]:
    """Convert raw training entries to instruction and chat formats."""
    instruction_dataset = []
    chat_dataset = []

    for data in entries:
        question = data["question"]
        chairman_answer = extract_chairman_verdict(data["chairman_answer"])
        sorted_responses = sort_responses_by_rank(data)

        # Instruction format (Alpaca-style)
        instruction_entry = {
            "id": data["id"],
            "domain": data.get("domain", "general"),
            "instruction": SYSTEM_PROMPT,
            "input": build_instruction_input(question, sorted_responses),
            "output": chairman_answer,
        }
        instruction_dataset.append(instruction_entry)

        # Chat format (ChatML-style)
        chat_entry = {
            "id": data["id"],
            "domain": data.get("domain", "general"),
            "messages": build_chat_messages(question, sorted_responses, chairman_answer),
        }
        chat_dataset.append(chat_entry)

    return instruction_dataset, chat_dataset


def split_dataset(dataset: list[dict], ratios: tuple[float, float, float],
                  seed: int = 42) -> tuple[list, list, list]:
    """Split dataset into train/val/test with deterministic shuffling."""
    # Sort by id hash for deterministic ordering
    sorted_data = sorted(dataset, key=lambda x: hashlib.md5(x["id"].encode()).hexdigest())
    random.seed(seed)
    random.shuffle(sorted_data)

    n = len(sorted_data)
    train_end = int(n * ratios[0])
    val_end = train_end + int(n * ratios[1])

    return sorted_data[:train_end], sorted_data[train_end:val_end], sorted_data[val_end:]


def compute_stats(entries: list[dict], instruction_dataset: list[dict]) -> dict:
    """Compute dataset statistics."""
    domains = Counter(e.get("domain", "unknown") for e in entries)

    input_lengths = [len(d["input"]) for d in instruction_dataset]
    output_lengths = [len(d["output"]) for d in instruction_dataset]

    # Estimate token counts (rough: 1 token ≈ 4 chars)
    input_tokens = [l // 4 for l in input_lengths]
    output_tokens = [l // 4 for l in output_lengths]

    return {
        "total_examples": len(entries),
        "domains": dict(domains.most_common()),
        "input_chars": {
            "min": min(input_lengths),
            "max": max(input_lengths),
            "mean": sum(input_lengths) // len(input_lengths),
        },
        "output_chars": {
            "min": min(output_lengths),
            "max": max(output_lengths),
            "mean": sum(output_lengths) // len(output_lengths),
        },
        "estimated_tokens": {
            "input": {
                "min": min(input_tokens),
                "max": max(input_tokens),
                "mean": sum(input_tokens) // len(input_tokens),
                "total": sum(input_tokens),
            },
            "output": {
                "min": min(output_tokens),
                "max": max(output_tokens),
                "mean": sum(output_tokens) // len(output_tokens),
                "total": sum(output_tokens),
            },
        },
    }


def write_jsonl(data: list[dict], path: Path):
    """Write a list of dicts to a JSONL file."""
    with open(path, "w") as f:
        for entry in data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Build fine-tuning dataset")
    parser.add_argument("--output-dir", type=str, default="data/dataset")
    parser.add_argument("--split-ratio", nargs=3, type=float,
                        default=[0.8, 0.1, 0.1],
                        help="Train/val/test split ratios")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    print("━" * 60)
    print("📦 Building Chairman Fine-Tuning Dataset")
    print("━" * 60)

    # Step 1: Load and validate
    print("\n📂 Loading training files...")
    entries = load_training_files()
    if not entries:
        print("❌ No valid training files found!")
        return

    # Step 2: Build datasets
    print("\n🔨 Building instruction & chat datasets...")
    instruction_ds, chat_ds = build_dataset(entries)
    print(f"  ✅ {len(instruction_ds)} instruction examples")
    print(f"  ✅ {len(chat_ds)} chat examples")

    # Step 3: Split
    print(f"\n✂️  Splitting ({args.split_ratio[0]:.0%}/{args.split_ratio[1]:.0%}/{args.split_ratio[2]:.0%})...")
    train_inst, val_inst, test_inst = split_dataset(
        instruction_ds, tuple(args.split_ratio), args.seed
    )
    train_chat, val_chat, test_chat = split_dataset(
        chat_ds, tuple(args.split_ratio), args.seed
    )
    print(f"  Train: {len(train_inst)} | Val: {len(val_inst)} | Test: {len(test_inst)}")

    # Step 4: Write files
    print(f"\n💾 Writing to {output}/...")

    # Full datasets
    write_jsonl(instruction_ds, output / "instruction_dataset.jsonl")
    write_jsonl(chat_ds, output / "chat_dataset.jsonl")

    # Splits — instruction format
    write_jsonl(train_inst, output / "train.jsonl")
    write_jsonl(val_inst, output / "val.jsonl")
    write_jsonl(test_inst, output / "test.jsonl")

    # Splits — chat format
    write_jsonl(train_chat, output / "train_chat.jsonl")
    write_jsonl(val_chat, output / "val_chat.jsonl")
    write_jsonl(test_chat, output / "test_chat.jsonl")

    # Step 5: Stats
    print("\n📊 Computing statistics...")
    stats = compute_stats(entries, instruction_ds)
    stats["split"] = {
        "train": len(train_inst),
        "val": len(val_inst),
        "test": len(test_inst),
    }
    with open(output / "dataset_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    # Step 6: Summary
    print(f"\n{'━' * 60}")
    print(f"✅ Dataset built successfully!")
    print(f"{'━' * 60}")
    print(f"\n📁 Output files in {output}/:")
    print(f"   instruction_dataset.jsonl  — Full Alpaca-style dataset ({len(instruction_ds)} examples)")
    print(f"   chat_dataset.jsonl         — Full ChatML-style dataset ({len(chat_ds)} examples)")
    print(f"   train.jsonl                — Training split ({len(train_inst)} examples)")
    print(f"   val.jsonl                  — Validation split ({len(val_inst)} examples)")
    print(f"   test.jsonl                 — Test split ({len(test_inst)} examples)")
    print(f"   train_chat.jsonl           — Training split, chat format")
    print(f"   val_chat.jsonl             — Validation split, chat format")
    print(f"   test_chat.jsonl            — Test split, chat format")
    print(f"   dataset_stats.json         — Statistics")

    print(f"\n📊 Stats:")
    print(f"   Domains:          {stats['domains']}")
    print(f"   Avg input tokens: ~{stats['estimated_tokens']['input']['mean']}")
    print(f"   Avg output tokens:~{stats['estimated_tokens']['output']['mean']}")
    print(f"   Total tokens:     ~{stats['estimated_tokens']['input']['total'] + stats['estimated_tokens']['output']['total']}")
    print(f"{'━' * 60}")


if __name__ == "__main__":
    main()
