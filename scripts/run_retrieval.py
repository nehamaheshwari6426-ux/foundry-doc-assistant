"""
scripts/run_retrieval.py

Smoke test for src/retrieval.py — Phase 5 close-out.

Runs a handful of sample questions through retrieve() and prints
top-k chunks with distances and text previews, so you can eyeball
whether retrieval is behaving sanely before wiring generation on top.

Run from anywhere (path fix below handles it), but project root is standard:
    python scripts/run_retrieval.py

Question source: notes/golden_set_brainstorm.md (W2 brain-dump).
Pick 3–5 questions from there and paste them into SAMPLE_QUESTIONS below —
per the W7 agenda, don't add *new* questions in this session, that's W8.
"""

import sys
from pathlib import Path

# Ensure the project root (parent of scripts/) is on sys.path, so `src`
# resolves regardless of how this script is invoked. Running
# `python scripts/run_retrieval.py` puts scripts/ on sys.path[0], not the
# project root — this line fixes that without needing PYTHONPATH set
# manually or the package installed in editable mode.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.retrieval import retrieve

# TODO: replace with 3–5 questions pulled from notes/golden_set_brainstorm.md
SAMPLE_QUESTIONS = [
    "What is Model router in Azure AI Foundry? and what do they do?",
    "How many models are supported by Model router? List name of latest 10 with purpose of model.",
    "How can I avoid incurring charges on unused services and resources in Foundary?",
]


def run():
    for question in SAMPLE_QUESTIONS:
        print("=" * 80)
        print(f"Q: {question}")
        print("-" * 80)
        chunks = retrieve(question, k=5)
        for i, c in enumerate(chunks, start=1):
            preview = c["text"][:150].replace("\n", " ")
            print(f"  [{i}] id={c['id']}  distance={c['distance']:.4f}")
            print(f"      {preview}...")
        print()


if __name__ == "__main__":
    run()