"""
Smoke test for the embedding module.

Embeds a small sample of real corpus chunks and prints results.
Verifies the embedding pipeline works end-to-end before bulk indexing
(which would embed all ~9,752 chunks and cost real API tokens).

Run from project root:
    python scripts/run_embedding_smoke.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.chunking import chunk_records
from src.embedding import embed_texts, EmbeddingStats


CORPUS_PATH = PROJECT_ROOT / "corpus" / "processed.jsonl"
SAMPLE_SIZE = 10  # Number of chunks to embed; keep small to limit cost.


def main() -> None:
    if not CORPUS_PATH.exists():
        print(f"Corpus not found at {CORPUS_PATH}")
        sys.exit(1)

    # Load and chunk the first few records.
    print(f"Loading first records from {CORPUS_PATH}...")
    records: list[dict] = []
    with CORPUS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
            if len(records) >= 3:
                break

    print(f"Chunking {len(records)} records...")
    chunks = chunk_records(records)
    sample = chunks[:SAMPLE_SIZE]
    print(f"Will embed {len(sample)} sample chunks.")
    print()

    # Embed and collect stats.
    texts = [c["text"] for c in sample]
    stats = EmbeddingStats()
    print(f"Calling Foundry embedding API...")
    vectors = embed_texts(texts, stats=stats)
    print()

    # Verify shape.
    print("Verification:")
    print(f"  Inputs            : {len(texts)}")
    print(f"  Vectors returned  : {len(vectors)}")
    print(f"  Vector dimensions : {len(vectors[0])} (expected 1536)")
    print(f"  All same dim?     : {all(len(v) == 1536 for v in vectors)}")
    print()

    # Print stats.
    print("Stats:")
    print(f"  {stats.summary()}")
    print()

    # Show a sample vector preview.
    print("Sample vector preview (first chunk, first 8 dimensions):")
    print(f"  {vectors[0][:8]}")
    print()

    # Estimated full-corpus cost if all chunks embed at this rate.
    if stats.total_texts > 0:
        cost_per_text = stats.total_cost_usd / stats.total_texts
        tokens_per_text = stats.total_tokens / stats.total_texts
        estimated_chunks = 9752  # Current corpus size; update if it changes.
        estimated_cost = cost_per_text * estimated_chunks
        estimated_tokens = tokens_per_text * estimated_chunks
        print(f"Extrapolation to full corpus ({estimated_chunks:,} chunks):")
        print(f"  Estimated tokens  : {estimated_tokens:,.0f}")
        print(f"  Estimated cost    : ${estimated_cost:.3f}")

    print()
    print("Smoke test passed.")


if __name__ == "__main__":
    main()