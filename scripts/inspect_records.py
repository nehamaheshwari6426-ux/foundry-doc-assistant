"""
Inspect random corpus records for manual quality review.

Pulls records from corpus/processed.jsonl, shows their cleaned content,
and flags a few heuristic warnings to surface suspicious records. The
eye is still the judge — this script speeds up sampling and side-by-side
comparison; it doesn't replace review.

Heuristics flagged:
- Leftover MS docs syntax in cleaned output (`:::`, `[!INCLUDE`, `[!NOTE]`,
  `<xref:`, etc.) — the cleaning pipeline missed something
- Cleaned output suspiciously shorter than source (possible content loss)
- Missing title, or title that looks like a filename fallback

Usage:
    python scripts/inspect_records.py                       # 5 random records
    python scripts/inspect_records.py -n 10                 # 10 random records
    python scripts/inspect_records.py --seed 42             # reproducible sample
    python scripts/inspect_records.py --id abc123def456     # specific record
    python scripts/inspect_records.py --id abc123 --show-source

Pipe to less for paged review:
    python scripts/inspect_records.py -n 10 | less
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

CORPUS_PATH = Path("corpus/processed.jsonl")
SOURCE_ROOT = Path("corpus/source")

# After INCLUDE resolution, cleaned content is often LARGER than source,
# so a low ratio is a strong signal that content was lost in cleaning.
MIN_CLEANED_VS_SOURCE_RATIO = 0.3

# Patterns that should NEVER appear in cleaned output. If they do, the
# cleaning pipeline missed a case.
SUSPICIOUS_PATTERNS = [
    (":::", "leftover MS directive"),
    ("[!INCLUDE", "unresolved INCLUDE"),
    ("[!NOTE]", "raw alert marker"),
    ("[!TIP]", "raw alert marker"),
    ("[!WARNING]", "raw alert marker"),
    ("[!IMPORTANT]", "raw alert marker"),
    ("[!CAUTION]", "raw alert marker"),
    ("<xref:", "raw xref"),
]


def load_records() -> list[dict]:
    if not CORPUS_PATH.exists():
        sys.exit(
            f"Corpus not found at {CORPUS_PATH}. "
            f"Run scripts/prepare_corpus.py first."
        )
    with CORPUS_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def source_text(record: dict) -> str | None:
    source_path = SOURCE_ROOT / record["source_path"]
    try:
        return source_path.read_text(encoding="utf-8", errors="replace")
    except (FileNotFoundError, OSError):
        return None


def detect_issues(record: dict, source: str | None) -> list[str]:
    issues = []
    cleaned = record["content"]

    # Leftover syntax — should be zero hits in any cleaned record
    for pattern, label in SUSPICIOUS_PATTERNS:
        if pattern in cleaned:
            issues.append(f"{label} found ({pattern!r})")

    # Length ratio — only meaningful if source exists
    if source and len(source) > 0:
        ratio = len(cleaned) / len(source)
        if ratio < MIN_CLEANED_VS_SOURCE_RATIO:
            issues.append(
                f"cleaned is {ratio:.0%} of source — possible content loss"
            )

    # Title sanity
    title = record.get("title", "")
    stem = Path(record["source_path"]).stem
    if not title:
        issues.append("title is empty")
    elif title == stem:
        issues.append(f"title looks like filename fallback ({title!r})")

    return issues


def print_record(record: dict, source: str | None, issues: list[str],
                 idx: int, total: int, show_source: bool) -> None:
    bar = "=" * 78
    print(f"\n{bar}")
    print(f"  Record {idx + 1}/{total}  |  id: {record['id']}")
    print(f"  Title : {record.get('title', '(missing)')}")
    print(f"  Path  : {record['source_path']}")
    if record.get("ms_date"):
        print(f"  Date  : {record['ms_date']}")
    print(bar)

    if issues:
        print("\n  [FLAGS]")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n  [no automatic flags — review by eye]")

    cleaned = record["content"]
    if source:
        ratio = len(cleaned) / len(source)
        print(f"\n  Source : {len(source):>6} chars")
        print(f"  Cleaned: {len(cleaned):>6} chars  ({ratio:.0%} of source)")
    else:
        print(f"\n  Cleaned: {len(cleaned)} chars  (source file not found)")

    if show_source and source:
        print("\n  --- SOURCE MARKDOWN ---\n")
        print(source)

    print("\n  --- CLEANED CONTENT ---\n")
    print(cleaned)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect random corpus records for manual quality review."
    )
    parser.add_argument("-n", "--num", type=int, default=5,
                        help="Number of random records to inspect (default: 5)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducible sampling")
    parser.add_argument("--id", type=str, default=None,
                        help="Inspect a specific record by id")
    parser.add_argument("--show-source", action="store_true",
                        help="Also print the source markdown alongside cleaned")
    args = parser.parse_args()

    records = load_records()

    if args.id:
        selection = [r for r in records if r["id"] == args.id]
        if not selection:
            sys.exit(f"No record with id={args.id!r}")
        seed_used = None
    else:
        # Auto-generate a seed if not given, so every sample is reproducible
        seed_used = args.seed if args.seed is not None else random.randint(0, 2**31 - 1)
        random.seed(seed_used)
        selection = random.sample(records, min(args.num, len(records)))

    print(f"Inspecting {len(selection)} record(s) from {len(records)} total in corpus")
    if seed_used is not None:
        print(f"Sample seed: {seed_used}  (reproduce this sample: --seed {seed_used})")

    flagged_records: list[tuple[dict, list[str]]] = []
    for i, record in enumerate(selection):
        source = source_text(record)
        issues = detect_issues(record, source)
        if issues:
            flagged_records.append((record, issues))
        print_record(record, source, issues, i, len(selection), args.show_source)

    print(f"\n{'=' * 78}")
    print(f"Reviewed {len(selection)} record(s); {len(flagged_records)} flagged for review.")

    if flagged_records:
        print("\nFlagged records (review needed):")
        for record, issues in flagged_records:
            title = record.get("title") or "(no title)"
            print(f"  - {record['id']}  {title!r}")
            for issue in issues:
                print(f"      - {issue}")
    if seed_used is not None:
        print(f"\nReproduce this sample: --seed {seed_used}")


if __name__ == "__main__":
    main()