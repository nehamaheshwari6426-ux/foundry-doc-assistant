"""
src/retrieval.py

Phase 5 — Retrieval module for foundry-doc-assistant.

Public contract:
    retrieve(query, k=5, collection_name=DEFAULT_COLLECTION) -> list[dict]

Returns a list of {id, text, metadata, distance}, ordered by ascending
cosine distance (closest match first).

Design decisions (confirmed W7 session):
- Distances are cosine, surfaced as-is — no re-normalisation to another metric.
  (Matches index.py's DISTANCE_METRIC = "cosine", set at collection creation.)
- No filtering on weak matches at this stage. If the lowest distance for a
  query is > WEAK_MATCH_THRESHOLD, we log a warning but still return results.
- Logging goes to stdout. Structured logging is Phase 7 work.
- No re-ranking, no hybrid search at v0.1 (both are Phase 6 candidates).
"""

from __future__ import annotations

from src.embedding import embed_texts, EmbeddingStats
from src.index import load_collection, DEFAULT_COLLECTION

WEAK_MATCH_THRESHOLD = 0.5


def retrieve(
    query: str,
    k: int = 5,
    collection_name: str = DEFAULT_COLLECTION,
    stats: EmbeddingStats | None = None,
) -> list[dict]:
    """
    Embed the query, search the index, return top-k chunks.

    Args:
        query: natural language question.
        k: number of chunks to return (default 5).
        collection_name: ChromaDB collection to search (default: foundry_docs_v1).
        stats: optional EmbeddingStats to accumulate query-embedding
            observability into (same object used during indexing, if you
            want cumulative cost/latency tracking across a session).

    Returns:
        List of dicts: {id, text, metadata, distance}, sorted by
        ascending distance (best match first).

    Raises:
        ValueError: if query is empty, or the collection doesn't exist
            (propagated from load_collection).
    """
    if not query or not query.strip():
        raise ValueError("retrieve() requires a non-empty query string")

    print(f"[retrieval] query={query!r} k={k} collection={collection_name}")

    # embed_texts takes a list and returns vectors in input order;
    # for a single query we send a singleton and take [0].
    query_embedding = embed_texts([query], stats=stats)[0]

    collection = load_collection(collection_name)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
    )

    # ChromaDB nests one level per query; we only sent one query.
    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    chunks = []
    for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
        chunks.append({
            "id": chunk_id,
            "text": text,
            "metadata": metadata,
            "distance": distance,
        })

    if chunks:
        best_distance = chunks[0]["distance"]
        if best_distance > WEAK_MATCH_THRESHOLD:
            print(
                f"[retrieval] WARNING weak match — best cosine distance "
                f"{best_distance:.4f} exceeds threshold {WEAK_MATCH_THRESHOLD}"
            )
        print(f"[retrieval] returned {len(chunks)} chunks, best distance={best_distance:.4f}")
    else:
        print("[retrieval] WARNING no chunks returned")

    return chunks


if __name__ == "__main__":
    # Minimal manual check — not the full smoke test (see scripts/run_retrieval.py)
    sample = retrieve("What is Azure AI Foundry?", k=3)
    for c in sample:
        preview = c["text"][:120].replace("\n", " ")
        print(f"  {c['id']}  dist={c['distance']:.4f}  {preview}...")