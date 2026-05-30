"""
Chunking module — splits prepared corpus records into chunks for embedding.

Strategy (v0.1): fixed-size character windows with overlap.
Chosen for simplicity, determinism, and ease of debugging.
Semantic chunking is a Phase 6 experiment, not a v0.1 choice.

Public contract:
    chunk_records(records, chunk_size=800, overlap=100) -> list[dict]

    Input record shape:  {id, title, path, content}
    Output chunk shape:  {id, text, metadata}
        where metadata = {source_id, title, path, chunk_index}
"""

from __future__ import annotations


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split a single text into overlapping fixed-size character chunks.

    The last chunk may be shorter than chunk_size.
    Always returns at least one chunk, even for empty input (returns [""]).
    """
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            f"overlap must be in [0, chunk_size), got {overlap} for chunk_size {chunk_size}"
        )

    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    step = chunk_size - overlap
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start += step
    return chunks


def chunk_records(
    records: list[dict],
    chunk_size: int = 800,
    overlap: int = 100,
) -> list[dict]:
    """Split records into overlapping chunks with provenance metadata.

    Args:
        records: list of records with shape {id, title, path, content}
        chunk_size: target chunk size in characters
        overlap: character overlap between consecutive chunks

    Returns:
        list of chunks with shape {id, text, metadata}
    """
    chunks: list[dict] = []
    for record in records:
        source_id = record["id"]
        title = record.get("title", "")
        path = record.get("path", "")
        content = record["content"]

        pieces = chunk_text(content, chunk_size=chunk_size, overlap=overlap)
        for i, piece in enumerate(pieces):
            chunks.append(
                {
                    "id": f"{source_id}::chunk-{i:03d}",
                    "text": piece,
                    "metadata": {
                        "source_id": source_id,
                        "title": title,
                        "path": path,
                        "chunk_index": i,
                    },
                }
            )
    return chunks