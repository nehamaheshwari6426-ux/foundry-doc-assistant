# `src/index.py` — Design Sketch

| | |
|---|---|
| **Status** | Design draft for W4 implementation |
| **Pipeline position** | Step 6 (Index persistence) in the RAG indexing phase |
| **Companion modules** | `src/chunking.py` (Step 4, done), `src/embedding.py` (Step 5, done), `src/retrieval.py` (Step 9, next) |
| **Reference** | RAG Solution Delivery Playbook §4.1 step 6, §5 step 6 |

---

## 1. Purpose

Persist chunk embeddings + metadata to disk in a ChromaDB collection so retrieval can run independently of indexing. Indexing runs once per corpus version; retrieval runs per query. The persistence layer is what makes this separation work.

## 2. Pipeline position

```
chunking.py output     →  embedding.py output      →  THIS MODULE  →  retrieval.py
(list[chunk dicts])       (list[1536-dim vectors])     (writes index)  (reads index)
```

`index.py` does not embed — it consumes embedding output. The embedding call sits inside `build_index`, but the actual `embed_texts` work lives in `embedding.py`. Same module reads the persisted index for retrieval (see §3).

## 3. Public interface

Three functions, one helper. Designed for v0.1 simplicity; Phase 6 may extend.

```python
def build_index(
    chunks: list[dict],
    collection_name: str = "foundry_docs_v1",
    batch_size: int = 100,
) -> EmbeddingStats:
    """
    Embed all chunks and upsert them into a persistent ChromaDB collection.

    Idempotent: re-running with the same chunks produces the same index
    (uses chunk IDs as ChromaDB IDs).
    """


def load_collection(
    collection_name: str = "foundry_docs_v1",
) -> chromadb.Collection:
    """
    Open the persistent ChromaDB collection for querying.

    Raises if the collection doesn't exist — call build_index first.
    """


def delete_collection(
    collection_name: str = "foundry_docs_v1",
) -> None:
    """
    Drop the collection entirely. Used when rebuilding from scratch
    (e.g., after a chunking strategy change makes existing chunks stale).
    """


def _get_client() -> chromadb.PersistentClient:
    """
    Internal: returns the persistent ChromaDB client rooted at
    ./data/index/. Caller never touches the client directly.
    """
```

**Why these three.** `build_index` is the indexing-phase entry point. `load_collection` is the retrieval-phase entry point. `delete_collection` is the corner-case for explicit invalidation (rare but needed when re-chunking). Everything else is internal.

## 4. Decisions committed at design time

These are locked unless evidence demands change. Each has a revisit trigger if applicable.

### 4.1 Persistence path: `./data/index/`

Already decided (this session). Chosen over `./chroma_db/` for separation of implementation from path naming, and to set up a `data/` namespace for later artifacts (`data/golden_set/`, `data/eval_results/`).

Gitignore entry required: add `data/index/` to `.gitignore` before first build. The index is regenerable from corpus + chunking + embedding — checking it into git would bloat the repo and create stale-state risk.

### 4.2 Collection name: `foundry_docs_v1`

Versioning is in the name. When chunking strategy or embedding model changes substantively, the version increments and a new collection is built. Old collections can be deleted explicitly via `delete_collection`.

**Revisit trigger:** any Phase 6 experiment that changes chunking strategy, chunk size, overlap, or embedding model produces a new versioned collection name (e.g., `foundry_docs_v2_semantic_chunks`). Side-by-side comparisons become possible without losing baselines.

### 4.3 Distance metric: cosine similarity

ChromaDB's default is L2 (squared euclidean). For OpenAI/Foundry embeddings, **cosine is the documented and recommended metric** — the embedding model is trained against cosine objectives, and L2 distance on normalised vectors approximates cosine but is less interpretable.

Configured at collection creation via `metadata={"hnsw:space": "cosine"}`. Once a collection has a distance metric set, it can't be changed — to switch, create a new versioned collection.

### 4.4 Idempotency strategy: upsert by chunk ID

ChromaDB supports `upsert(ids=..., embeddings=..., documents=..., metadatas=...)` — adds if new, updates if exists. Using chunk IDs (`{source_id}::chunk-{i:03d}`) as ChromaDB IDs means:

- Re-running `build_index` with the same chunks is safe (no duplicates)
- Re-running with modified content updates the embedding (new vector, same ID)
- Interrupted builds can be resumed by re-running

**Limitation:** upsert doesn't *remove* chunks that disappear between runs. If the corpus shrinks (records deleted, paths filtered out), stale chunks linger. Workaround: `delete_collection` + `build_index` for clean rebuilds. v0.1 expects clean rebuilds when scope changes.

### 4.5 Batch size for upserts: 100

ChromaDB recommends batched upserts for performance. 100 is conservative — large enough to amortise the per-call overhead, small enough that interrupted batches don't lose much progress. Aligns with embedding module's 64-chunk batches (after embedding completes, we have ~100-ish ready for ChromaDB).

**Revisit trigger:** if Phase 5 actual indexing wall time is unacceptable, tune up to 500. Phase 6 work, not v0.1.

### 4.6 Schema: what gets stored per chunk

| ChromaDB field | Value from chunk |
|---|---|
| `ids` | `chunk["id"]` (e.g., `2d16dfb54929::chunk-000`) |
| `embeddings` | from `embed_texts([chunk["text"]])` |
| `documents` | `chunk["text"]` (the raw chunk content) |
| `metadatas` | `chunk["metadata"]` (source_id, source_path, title, chunk_index) |

`documents` storage is *intentional* — ChromaDB stores the raw text alongside the vector, so retrieval returns both the match and its source text without a second lookup. Worth ~2-3x the storage cost of vectors-only, but saves a round-trip in every query. Standard practice for RAG.

## 5. Decisions deferred

Each with a named revisit trigger so they don't disappear.

| Deferral | Revisit trigger |
|---|---|
| **Per-chunk additional metadata fields** (ms_date for freshness, description for record-level context) | Phase 6 if retrieval results benefit from filtering on these |
| **Hybrid retrieval (vector + BM25)** | Phase 6 if pure-vector recall@k disappoints |
| **Contextual retrieval** (prepended chunk context before embedding) | Phase 6 chunking-strategy experiment phase |
| **Collection-level access control** | Phase 7 hardening; not needed for learning project |
| **Compression / quantisation of vectors** | Only relevant at much larger corpus scale (>100k chunks) |

## 6. Data flow during indexing

Sequential, batched, observable:

```
1. Load chunks (already in memory from chunking.py output, or read from disk)
2. Open / create collection at ./data/index/ via PersistentClient
3. For each batch of 100 chunks:
     a. Slice next 100 chunks
     b. Call embed_texts(texts=batch_texts, stats=accumulator)
     c. Build ChromaDB upsert args: ids, embeddings, documents, metadatas
     d. collection.upsert(...)
     e. Log batch progress (chunk count, elapsed time, cumulative cost)
4. Return final EmbeddingStats for full-run cost / latency summary
```

**Progress reporting matters.** At 9,752 chunks ÷ 64 embedding-batch + 100 chroma-batch = ~150 embedding calls + ~100 chroma calls + ~10 minutes total. The user must see progress, not silent execution.

## 7. Failure modes and handling

| Failure | Detection | Handling |
|---|---|---|
| Embedding API failure mid-build | `embed_texts` raises after retries | Propagate; partial index is fine (upsert + IDs means resume is safe) |
| ChromaDB write failure | `collection.upsert` raises | Propagate with clear context (which batch index, how many succeeded) |
| Disk full | OS error from PersistentClient | Propagate; surfaces cleanly |
| Collection name conflict (already exists with different schema) | ChromaDB raises | Caller can call `delete_collection` and retry |
| Interrupt (Ctrl+C) mid-build | Python KeyboardInterrupt | ChromaDB upserts are durable per-batch; restart picks up where it left off via upsert |

## 8. Open questions for Saturday

Things to validate during coding, not pre-decide:

1. **ChromaDB persistent vs ephemeral client.** `PersistentClient(path=...)` vs `Client()` — need to confirm `PersistentClient` is the right import for current ChromaDB version (1.5.9 pinned). Quick test before committing to the pattern.
2. **`upsert` vs `add` semantics in 1.5.9.** Confirm `upsert` exists at the Collection level in this version; older docs sometimes show `add` with `ids` doing upsert. 5-minute verification.
3. **Returning collection vs returning stats from `build_index`.** Current design returns `EmbeddingStats`. Question: should it also return the Collection object for immediate query testing? Lean: no — keep concerns separate, caller uses `load_collection` afterward.
4. **Whether to support a `dry_run=True` flag** that builds the embedding count and cost estimate without writing. Cheap to add; useful for "how long will this take?" before committing to full build. Recommend yes if it's <10 lines.

## 9. Pre-implementation checklist

Before writing code Saturday, verify:

- [ ] `data/index/` listed in `.gitignore`
- [ ] `pip install chromadb==1.5.9` already done (per requirements.txt — confirmed)
- [ ] ChromaDB 1.5.9 documentation skimmed for PersistentClient + upsert API
- [ ] `EmbeddingStats` import path works from `src.index`
- [ ] Approximate API cost for full indexing budgeted ($0.04 per ADR 0009 forecast)

## 10. Smoke test (companion script)

After implementation, `scripts/build_index.py`:

- Reads corpus → chunks (re-runs chunking, ~0.5s)
- Calls `build_index(chunks)` with progress reporting
- Prints final EmbeddingStats summary
- Calls `load_collection` and asserts `collection.count() == len(chunks)`
- Exit cleanly with success message

Estimated wall time: ~10 minutes (mostly embedding API). Estimated cost: ~$0.04.

---

## 11. What to write Saturday — order of work

1. `src/index.py` core: `_get_client`, `load_collection`, `delete_collection` (simple shapes, ~30 lines total)
2. `build_index` skeleton with batching loop (no embedding yet, just the ChromaDB plumbing)
3. Wire `embed_texts` into the batch loop
4. Add progress logging
5. `scripts/build_index.py` smoke test
6. Run, verify, commit

Estimated time: 60-90 minutes if no surprises. Add 30-min buffer for ChromaDB API quirks.

## 12. Open ADR candidates

If Saturday implementation surfaces decisions worth documenting:

- **ADR 0010 — Persistence path and gitignore** (small, but explicit)
- **ADR 0011 — Distance metric: cosine over L2** (justifies the non-default choice)

Don't pre-write these. Write them only if the decisions deserve explicit recording after implementation surfaces edge cases.