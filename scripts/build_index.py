"""
Build the full index from the prepared corpus.

End-to-end Step 4 → 5 → 6 pipeline:
  1. Load prepared records from corpus/processed.jsonl
  2. Chunk them via src.chunking
  3. Embed and upsert into ChromaDB via src.index

This is the smoke test for the indexing module. After this runs cleanly,
retrieval (Step 9) can read from the persisted collection.

Run from project root:
    python scripts/build_index.py

Estimated cost: ~$0.04 for the current corpus (~9,752 chunks).
Estimated wall time: ~10 minutes (mostly embedding API latency).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.chunking import chunk_records
from src.index import build_index, load_collection, DEFAULT_COLLECTION


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


def main() -> None:
    if not CORPUS_PATH.exists():
        print(f"Corpus not found at {CORPUS_PATH}")
        print("Run scripts/fetch_corpus.sh and scripts/prepare_corpus.py first.")
        sys.exit(1)

    print(f"Loading records from {CORPUS_PATH}...")
    records = load_records(CORPUS_PATH)
    print(f"  {len(records)} records loaded.")

    print(f"Chunking records...")
    chunks = chunk_records(records)
    
    # Add this line just below to test on a small slice:
    # chunks = chunks[:5]   # remove this line once verified

    print(f"  {len(chunks):,} chunks produced.")
    print()

    # Build the index. This is the slow part.
    stats = build_index(chunks, collection_name=DEFAULT_COLLECTION)

    # Verify by reading back what was just written.
    print()
    print("Verifying collection...")
    collection = load_collection(DEFAULT_COLLECTION)
    count = collection.count()
    print(f"  Collection '{DEFAULT_COLLECTION}' has {count:,} chunks.")

    if count != len(chunks):
        print(
            f"  WARNING: expected {len(chunks):,} chunks, found {count:,}. "
            f"Some upserts may have failed or chunks may have collided on ID."
        )
        sys.exit(1)

    # Spot-check one chunk by ID lookup.
    sample_id = chunks[0]["id"]
    result = collection.get(ids=[sample_id], include=["documents", "metadatas"])
    if not result["ids"]:
        print(f"  WARNING: sample chunk {sample_id} not found in collection.")
        sys.exit(1)

    print(f"  Spot-check: chunk '{sample_id}' is in the index.")
    print(f"    title: {result['metadatas'][0].get('title', '(no title)')}")
    print(f"    doc preview: {result['documents'][0][:80]}...")
    print()
    print("Build complete. Index is ready for retrieval.")


if __name__ == "__main__":
    main()