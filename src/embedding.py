"""
Embedding module — Step 5 of the RAG indexing pipeline, also used at
Step 8 (query embedding).

Wraps the Foundry/OpenAI embeddings API behind a stable interface:
batched calls, exponential-backoff retries, and per-batch observability.

Public contract:
    embed_texts(texts) -> list[list[float]]
        Embeds a list of texts. Returns vectors in the same order as inputs.
        For a single text, pass [text] and take [0] from the result.

    EmbeddingStats
        Per-call statistics: total tokens, total cost, total latency,
        number of batches, number of retries.

See ADR 0002 for stack choice (text-embedding-3-small, 1536 dimensions).
See Playbook §5 step 5 for the quality controls implemented here.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable

from openai import OpenAI, APIError, RateLimitError, APITimeoutError

from config import settings


# Defaults — sized for indexing throughput, not minimum latency.
DEFAULT_BATCH_SIZE = 64
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0

# Cost (USD per 1M tokens) for text-embedding-3-small as of 2026-05.
# Source: Microsoft pricing; verify quarterly. Used for observability only.
COST_PER_1M_TOKENS_USD = 0.020


@dataclass
class EmbeddingStats:
    """Aggregate statistics from one or more embed_texts calls."""

    total_texts: int = 0
    total_tokens: int = 0
    total_batches: int = 0
    total_retries: int = 0
    total_latency_seconds: float = 0.0
    batch_latencies: list[float] = field(default_factory=list)

    @property
    def total_cost_usd(self) -> float:
        return (self.total_tokens / 1_000_000) * COST_PER_1M_TOKENS_USD

    @property
    def mean_batch_latency_seconds(self) -> float:
        if not self.batch_latencies:
            return 0.0
        return sum(self.batch_latencies) / len(self.batch_latencies)

    def summary(self) -> str:
        return (
            f"texts={self.total_texts}, "
            f"tokens={self.total_tokens:,}, "
            f"batches={self.total_batches}, "
            f"retries={self.total_retries}, "
            f"total_latency={self.total_latency_seconds:.1f}s, "
            f"mean_batch_latency={self.mean_batch_latency_seconds:.2f}s, "
            f"cost=${self.total_cost_usd:.4f}"
        )


def _client() -> OpenAI:
    return OpenAI(
        base_url=settings.foundry_base_url,
        api_key=settings.foundry_api_key,
    )


def _embed_one_batch(
    client: OpenAI,
    batch: list[str],
    stats: EmbeddingStats,
) -> list[list[float]]:
    """Embed a single batch with retries. Updates stats in place."""
    backoff = INITIAL_BACKOFF_SECONDS
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            start = time.monotonic()
            response = client.embeddings.create(
                model=settings.embedding_deployment,
                input=batch,
            )
            elapsed = time.monotonic() - start

            # Record successful-batch stats.
            stats.total_batches += 1
            stats.total_tokens += response.usage.total_tokens
            stats.total_latency_seconds += elapsed
            stats.batch_latencies.append(elapsed)

            # Vectors come back in the same order as inputs; verify.
            vectors = [item.embedding for item in response.data]
            if len(vectors) != len(batch):
                raise RuntimeError(
                    f"Expected {len(batch)} vectors, got {len(vectors)}. "
                    f"Response ordering invariant violated."
                )
            return vectors

        except (RateLimitError, APITimeoutError) as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                stats.total_retries += 1
                time.sleep(backoff)
                backoff *= 2
                continue
            raise

        except APIError as exc:
            # Non-transient API errors fail immediately; not all errors are
            # safely retryable (e.g., 400 from bad input).
            raise RuntimeError(
                f"Foundry embedding API error: {type(exc).__name__}: {exc}"
            ) from exc

    # Exhausted retries on a transient error.
    raise RuntimeError(
        f"Foundry embedding API failed after {MAX_RETRIES} retries. "
        f"Last error: {last_error}"
    ) from last_error


def embed_texts(
    texts: Iterable[str],
    batch_size: int = DEFAULT_BATCH_SIZE,
    stats: EmbeddingStats | None = None,
) -> list[list[float]]:
    """Embed a list of texts via Foundry. Returns vectors in input order.

    Args:
        texts: Iterable of strings to embed. Empty strings are not allowed
            (embedding API rejects them).
        batch_size: Number of texts to send per API call. Lower for tighter
            cost/failure granularity; higher for fewer calls.
        stats: Optional EmbeddingStats to accumulate observability data.
            If None, a fresh stats object is used internally.

    Returns:
        List of embedding vectors. Each vector is a list of floats with
        dimensionality matching the embedding model (1536 for
        text-embedding-3-small).

    Raises:
        ValueError: If batch_size <= 0 or texts contains an empty string.
        RuntimeError: On API failure after retries are exhausted.
    """
    if batch_size <= 0:
        raise ValueError(f"batch_size must be positive, got {batch_size}")

    texts = list(texts)
    if any(not t for t in texts):
        raise ValueError(
            "Empty strings are not allowed in texts; "
            "filter them out before calling embed_texts."
        )

    if stats is None:
        stats = EmbeddingStats()
    stats.total_texts += len(texts)

    if not texts:
        return []

    client = _client()
    all_vectors: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        vectors = _embed_one_batch(client, batch, stats)
        all_vectors.extend(vectors)

    return all_vectors