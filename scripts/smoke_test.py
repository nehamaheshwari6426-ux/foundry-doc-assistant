"""
Smoke test for Azure Foundry connectivity.

Runs a minimal chat completion and a minimal embedding call against the
configured deployments and prints the results. If both succeed, the
configuration is correct and Phase 5 build work can proceed.

Run from project root:
    python scripts/smoke_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# When running scripts/smoke_test.py from project root, ensure project root
# is importable so `from config import settings` works.
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from openai import OpenAI

from config import settings


def main() -> None:
    client = OpenAI(
        base_url=settings.foundry_base_url,
        api_key=settings.foundry_api_key,
    )

    print(f"Foundry base URL    : {settings.foundry_base_url}")
    print(f"Generator deployment: {settings.generator_deployment}")
    print(f"Embedding deployment: {settings.embedding_deployment}")
    print()

    # --- Test 1: chat completion -------------------------------------------
    print("Testing chat completion...")
    try:
        response = client.chat.completions.create(
            model=settings.generator_deployment,
            messages=[
                {"role": "user", "content": "Reply with the single word: connected."}
            ],
            max_tokens=10,
        )
        reply = response.choices[0].message.content
        print(f"  OK   response: {reply!r}")
    except Exception as exc:
        print(f"  FAIL chat completion error: {type(exc).__name__}: {exc}")
        sys.exit(1)

    # --- Test 2: embedding -------------------------------------------------
    print()
    print("Testing embedding...")
    try:
        response = client.embeddings.create(
            model=settings.embedding_deployment,
            input=["hello, world"],
        )
        vector = response.data[0].embedding
        print(f"  OK   embedding dimension: {len(vector)}")
    except Exception as exc:
        print(f"  FAIL embedding error: {type(exc).__name__}: {exc}")
        sys.exit(1)

    print()
    print("All smoke tests passed. Azure Foundry connection is working.")


if __name__ == "__main__":
    main()