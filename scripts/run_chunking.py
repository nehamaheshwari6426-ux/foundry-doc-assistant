"""
Smoke test for the chunking module.

Reads the prepared corpus JSONL, runs chunk_records, and prints summary
statistics. Verifies the module works on real data before Phase 5
continues to embedding and indexing.

Run from project root:
    python scripts/run_chunking.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.chunking import chunk_records

CORPUS_PATH = PROJECT_ROOT / "corpus" / "processed.jsonl"

def load_records(path: Path) -> list[dict]:
    """Load JSONL records from disk."""
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def summarise(records: list[dict], chunks: list[dict]) -> None:
    """Print summary statistics about chunking results."""
    print(f"Records loaded         : {len(records)}")
    print(f"Chunks produced        : {len(chunks)}")
    print(f"Avg chunks per record  : {len(chunks) / len(records):.1f}")
    print()

    # Chunk length distribution
    lengths = [len(c["text"]) for c in chunks]
    print(f"Chunk length (chars)")
    print(f"  min                  : {min(lengths)}")
    print(f"  max                  : {max(lengths)}")
    print(f"  mean                 : {statistics.mean(lengths):.0f}")
    print(f"  median               : {statistics.median(lengths):.0f}")
    print()

    # Chunks per record distribution
    chunks_per_record: dict[str, int] = {}
    for chunk in chunks:
        source = chunk["metadata"]["source_id"]
        chunks_per_record[source] = chunks_per_record.get(source, 0) + 1
    cpr = list(chunks_per_record.values())
    print(f"Chunks per record")
    print(f"  min                  : {min(cpr)}")
    print(f"  max                  : {max(cpr)}")
    print(f"  median               : {statistics.median(cpr):.0f}")
    print()

    # Sample chunks for spot-check
    print("Sample chunks (first record):")
    first_source = chunks[0]["metadata"]["source_id"]
    samples = [c for c in chunks if c["metadata"]["source_id"] == first_source][:3]
    for c in samples:
        preview = c["text"][:120].replace("\n", " ")
        print(f"  [{c['id']}] {preview}...")


def main() -> None:
    if not CORPUS_PATH.exists():
        print(f"Corpus not found at {CORPUS_PATH}")
        print("Run scripts/fetch_corpus.sh and scripts/prepare_corpus.py first.")
        sys.exit(1)

    print(f"Loading records from {CORPUS_PATH}...")
    records = load_records(CORPUS_PATH)

    print("Running chunk_records with default parameters (800/100)...")
    print()
    chunks = chunk_records(records)
    summarise(records, chunks)


if __name__ == "__main__":
    main()