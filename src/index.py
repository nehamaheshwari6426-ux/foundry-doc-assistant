"""
Index module — Step 6 of the RAG indexing pipeline.

Persists chunk embeddings and metadata to a local ChromaDB collection so
the retrieval phase can run independently of indexing. Indexing runs once
per corpus version; retrieval runs per query against the persisted index.

See docs/design/index-module-design-sketch.md for design rationale.
See RAG Solution Delivery Playbook §4.1 step 6 and §5 step 6.
"""

from __future__ import annotations

import time
from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings as ChromaSettings

from src.embedding import embed_texts, EmbeddingStats


# Where the persistent index lives on disk. See ADR 0009 (cost posture)
# and the design sketch §4.1 (persistence path decision).
INDEX_PATH = Path("data/index")

# Default collection name. Versioning baked in so chunking-strategy
# experiments in Phase 6 can build alternative collections without
# overwriting the baseline. See design sketch §4.2.
DEFAULT_COLLECTION = "foundry_docs_v1"

# Cosine over the ChromaDB default L2. text-embedding-3-small is trained
# against cosine objectives; using L2 is the wrong ruler. See design
# sketch §4.3.
DISTANCE_METRIC = "cosine"

# Upsert batch size for ChromaDB writes. Aligns roughly with embedding
# module's batch size (64) so each round of embeddings flows into one
# ChromaDB upsert without buffering. See design sketch §4.5.
DEFAULT_BATCH_SIZE = 100


def _get_client() -> chromadb.PersistentClient:
    """Return a persistent ChromaDB client rooted at INDEX_PATH."""
    INDEX_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(INDEX_PATH),
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def _get_or_create_collection(
    client: chromadb.PersistentClient,
    collection_name: str,
) -> Collection:
    """
    Get the collection if it exists, create it if not.

    Sets the distance metric at creation time via hnsw:space metadata.
    The metric cannot be changed after creation — to switch metrics,
    delete the collection and rebuild.
    """
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": DISTANCE_METRIC},
    )


def load_collection(
    collection_name: str = DEFAULT_COLLECTION,
) -> Collection:
    """
    Open the persistent ChromaDB collection for querying.

    Used by the retrieval phase. Raises if the collection doesn't exist
    yet — call build_index first.

    Args:
        collection_name: Name of the collection to load.

    Returns:
        The ChromaDB Collection object.

    Raises:
        ValueError: If the collection doesn't exist.
    """
    client = _get_client()
    try:
        return client.get_collection(name=collection_name)
    except Exception as exc:
        raise ValueError(
            f"Collection '{collection_name}' does not exist at {INDEX_PATH}. "
            f"Run build_index first."
        ) from exc


def delete_collection(
    collection_name: str = DEFAULT_COLLECTION,
) -> None:
    """
    Drop the named collection entirely.

    Used when rebuilding from scratch — e.g., after a chunking strategy
    change makes existing chunks stale, or when scope changes mean some
    chunks should no longer be in the index.

    Args:
        collection_name: Name of the collection to delete.

    Raises:
        Exception: If the collection doesn't exist (ChromaDB-specific).
    """
    client = _get_client()
    client.delete_collection(name=collection_name)


def build_index(
    chunks: list[dict],
    collection_name: str = DEFAULT_COLLECTION,
    batch_size: int = DEFAULT_BATCH_SIZE,
    progress: bool = True,
) -> EmbeddingStats:
    """
    Embed all chunks and upsert them into a persistent ChromaDB collection.

    Idempotent by chunk ID: re-running with the same chunks produces the
    same index. Interrupted runs can be resumed by re-running (upsert
    skips work already done because chunk IDs are stable).

    Note: upsert does NOT remove chunks that disappear between runs.
    If the corpus shrinks, call delete_collection first.

    Args:
        chunks: List of chunks per chunking.py's contract:
            {id, text, metadata: {source_id, source_path, title, chunk_index}}
        collection_name: ChromaDB collection name (default: foundry_docs_v1).
        batch_size: Number of chunks per ChromaDB upsert call.
        progress: If True, print per-batch progress to stdout.

    Returns:
        EmbeddingStats with cumulative tokens, batches, retries, latency, cost.
    """
    if not chunks:
        raise ValueError("chunks is empty; nothing to index.")

    client = _get_client()
    collection = _get_or_create_collection(client, collection_name)

    stats = EmbeddingStats()
    total_chunks = len(chunks)
    start_time = time.monotonic()

    if progress:
        print(f"Indexing {total_chunks:,} chunks into '{collection_name}'...")
        print(f"  persistence path: {INDEX_PATH}")
        print(f"  distance metric : {DISTANCE_METRIC}")
        print(f"  batch size      : {batch_size}")
        print()

    for batch_start in range(0, total_chunks, batch_size):
        batch_end = min(batch_start + batch_size, total_chunks)
        batch = chunks[batch_start:batch_end]

        # Embed this batch via the existing embedding wrapper.
        texts = [c["text"] for c in batch]
        vectors = embed_texts(texts, stats=stats)

        # Upsert into ChromaDB. IDs are chunk IDs (stable across runs);
        # documents store the raw chunk text alongside the vector;
        # metadatas carry source provenance for citation.
        ids = [c["id"] for c in batch]
        documents = [c["text"] for c in batch]
        metadatas = [c["metadata"] for c in batch]

        collection.upsert(
            ids=ids,
            embeddings=vectors,
            documents=documents,
            metadatas=metadatas,
        )

        if progress:
            elapsed = time.monotonic() - start_time
            done = batch_end
            pct = (done / total_chunks) * 100
            rate = done / elapsed if elapsed > 0 else 0
            print(
                f"  [{done:>5,}/{total_chunks:,}] {pct:5.1f}% "
                f"| elapsed {elapsed:6.1f}s "
                f"| {rate:6.1f} chunks/s "
                f"| cost so far ${stats.total_cost_usd:.4f}"
            )

    if progress:
        elapsed_total = time.monotonic() - start_time
        print()
        print(f"Indexing complete in {elapsed_total:.1f}s.")
        print(f"Collection '{collection_name}' now has {collection.count():,} chunks.")
        print(f"Final stats: {stats.summary()}")

    return stats