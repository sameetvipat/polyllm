#!/usr/bin/env python3
"""
Phase 2: Data Preparation — Audit, clean, and regenerate training files.

Identifies training files where synthetic responses contain the "the topic"
placeholder (caused by _find_knowledge falling back when no KNOWLEDGE entry
matched). Regenerates those files using the fixed question-aware templates.

Usage:
    python scripts/prepare_training_data.py --audit          # report only
    python scripts/prepare_training_data.py --fix            # audit + regenerate bad files
    python scripts/prepare_training_data.py --validate       # check final dataset quality
    python scripts/prepare_training_data.py --fix --limit 50 # fix first 50 bad files
"""

import json
import argparse
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))
from generate_training_data import (
    MODELS, CHAIRMAN_MODEL, LABEL_MAP, TRAINING_DIR,
    _find_knowledge, _build_hermes, _build_llama, _build_gemma,
    _build_ranking, _build_chairman, _compute_aggregates,
)

QUARANTINE_DIR = TRAINING_DIR / "quarantine"
MIN_COUNCIL_WORDS   = 60   # minimum words per council response
MIN_CHAIRMAN_WORDS  = 80   # minimum words for chairman answer
PLACEHOLDER_SIGNAL  = "the topic is a"   # key marker of bad fallback responses


# ── Quality checks ────────────────────────────────────────────────────────────

def _has_placeholder(text: str) -> bool:
    return PLACEHOLDER_SIGNAL in text.lower()


def _is_empty_section(text: str) -> bool:
    """Detect templates where headers have no content (### Foo\n\n\n)."""
    return "###" in text and "\n\n\n" in text


def audit_file(path: Path) -> list[str]:
    """Return list of issue labels for a training file. Empty = clean."""
    try:
        data = json.load(open(path))
    except Exception:
        return ["malformed_json"]

    issues = []

    # Check council responses
    for r in data.get("council_responses", []):
        text = r.get("response", "")
        if _has_placeholder(text):
            issues.append("placeholder_response")
            break
        if _is_empty_section(text):
            issues.append("empty_sections")
            break
        if len(text.split()) < MIN_COUNCIL_WORDS:
            issues.append("short_response")
            break

    # Check chairman
    chairman = data.get("chairman_answer", "")
    if _has_placeholder(chairman):
        issues.append("placeholder_chairman")
    if len(chairman.split()) < MIN_CHAIRMAN_WORDS:
        issues.append("short_chairman")

    # Check question quality
    q = data.get("question", "")
    if not q or len(q) < 10:
        issues.append("missing_question")

    return list(set(issues))


# ── Regeneration ──────────────────────────────────────────────────────────────

def regenerate_file(path: Path) -> bool:
    """Regenerate council responses + chairman for a training file in place."""
    try:
        data = json.load(open(path))
    except Exception:
        return False

    question = data.get("question", "")
    domain   = data.get("domain", "general")
    qid      = data.get("id", path.stem)

    if not question:
        return False

    k = _find_knowledge(question, domain)

    responses = [
        {"model": MODELS[0], "response": _build_hermes(question, domain, k)},
        {"model": MODELS[1], "response": _build_llama(question, domain, k)},
        {"model": MODELS[2], "response": _build_gemma(question, domain, k)},
    ]
    rankings  = [_build_ranking(m, question, k) for m in MODELS]
    chairman  = _build_chairman(question, domain, k, responses, rankings)
    agg       = _compute_aggregates(rankings, LABEL_MAP)

    data["council_responses"]  = responses
    data["rankings"]           = rankings
    data["chairman_answer"]    = chairman
    data["chairman_model"]     = CHAIRMAN_MODEL
    data["aggregate_rankings"] = agg
    data["label_to_model"]     = LABEL_MAP

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Phase 2: Prepare training data")
    parser.add_argument("--audit",    action="store_true", help="Report quality issues only")
    parser.add_argument("--fix",      action="store_true", help="Audit + regenerate bad files")
    parser.add_argument("--validate", action="store_true", help="Validate final dataset quality")
    parser.add_argument("--limit",    type=int, default=0,
                        help="Max files to fix (0 = all)")
    args = parser.parse_args()

    if not any([args.audit, args.fix, args.validate]):
        parser.print_help()
        return

    all_files = sorted(TRAINING_DIR.glob("*.json"))
    print("━" * 65)
    print("📋 Phase 2: Training Data Preparation")
    print("━" * 65)
    print(f"   Training files found: {len(all_files)}\n")

    # ── Audit ─────────────────────────────────────────────────────────────────
    if args.audit or args.fix:
        print("🔍 Auditing files...")
        bad_files  = []
        good_files = []
        issue_counts = Counter()

        for f in all_files:
            issues = audit_file(f)
            if issues:
                bad_files.append((f, issues))
                for i in issues:
                    issue_counts[i] += 1
            else:
                good_files.append(f)

        print(f"\n   ✅ Clean files:  {len(good_files):4d} ({len(good_files)/len(all_files)*100:.1f}%)")
        print(f"   ❌ Bad files:    {len(bad_files):4d} ({len(bad_files)/len(all_files)*100:.1f}%)")
        print(f"\n   Issue breakdown:")
        for issue, count in issue_counts.most_common():
            print(f"     {issue:30s}: {count}")

        if args.audit and not args.fix:
            print(f"\n   Run with --fix to regenerate bad files.")
            return

        # ── Fix ───────────────────────────────────────────────────────────────
        if args.fix:
            to_fix = bad_files if not args.limit else bad_files[:args.limit]
            print(f"\n🔨 Regenerating {len(to_fix)} bad files...")

            fixed   = 0
            failed  = 0
            for i, (f, issues) in enumerate(to_fix):
                ok = regenerate_file(f)
                if ok:
                    fixed += 1
                else:
                    failed += 1

                if (i + 1) % 100 == 0:
                    print(f"   ✅ {i+1}/{len(to_fix)} processed...")

            print(f"\n   ✅ Regenerated: {fixed}")
            if failed:
                print(f"   ❌ Failed:      {failed}")

    # ── Validate ──────────────────────────────────────────────────────────────
    if args.validate:
        print("\n🧪 Validating dataset after cleaning...")
        all_files = sorted(TRAINING_DIR.glob("*.json"))
        bad_after = []
        domain_counts = Counter()
        chairman_lengths = []
        response_lengths = []

        for f in all_files:
            issues = audit_file(f)
            if issues:
                bad_after.append((f.name, issues))
            try:
                data = json.load(open(f))
                domain_counts[data.get("domain", "unknown")] += 1
                chairman_lengths.append(len(data.get("chairman_answer", "").split()))
                for r in data.get("council_responses", []):
                    response_lengths.append(len(r.get("response", "").split()))
            except Exception:
                pass

        total = len(all_files)
        clean = total - len(bad_after)
        print(f"\n   Total files:   {total}")
        print(f"   ✅ Clean:       {clean} ({clean/total*100:.1f}%)")
        print(f"   ❌ Still bad:   {len(bad_after)}")
        if bad_after:
            for name, issues in bad_after[:10]:
                print(f"     {name}: {issues}")

        if chairman_lengths:
            avg_ch = sum(chairman_lengths) / len(chairman_lengths)
            avg_rs = sum(response_lengths) / len(response_lengths)
            print(f"\n   Avg chairman words:  {avg_ch:.0f}")
            print(f"   Avg response words:  {avg_rs:.0f}")

        print(f"\n   Domain distribution:")
        for d, c in domain_counts.most_common():
            print(f"     {d:30s}: {c}")

        print(f"\n{'━' * 65}")
        if len(bad_after) == 0:
            print("✅ Dataset is clean — ready for fine-tuning.")
        else:
            print(f"⚠️  {len(bad_after)} files still need attention.")
            print("   Run with --fix again or inspect manually.")
        print("━" * 65)


if __name__ == "__main__":
    main()
