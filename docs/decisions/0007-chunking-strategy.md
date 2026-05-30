# ADR 0007 — Chunking Strategy: Fixed-Size Character with Overlap (v0.1)

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-05-30 |
| **Phase** | 5 (Baseline Build) |
| **Related** | ADR 0002 (Stack selection), RAG Solution Delivery Playbook §5 step 4 |

## Context

Step 4 of the RAG indexing pipeline (per `RAG_Solution_Delivery_Playbook.md`) splits prepared records into chunks suitable for embedding and retrieval. Chunking strategy is the single highest-leverage quality control in early RAG iteration — the playbook flags it explicitly. The choice made here directly shapes what retrieval can and cannot surface in Phase 6.

A v0.1 baseline must be chosen now so that Phase 5 can produce a working end-to-end pipeline with measurable numbers. Phase 6 experiments then have a baseline to beat.

Candidates considered:

1. **Fixed-size character chunking with overlap** — slide a fixed character window across content, with configurable overlap between consecutive chunks
2. **Token-based chunking** — same approach but counted in model tokens via tiktoken
3. **Sentence-aware chunking** — split on sentence boundaries via NLP library
4. **Semantic chunking** — split on detected semantic-similarity drops between consecutive sentences
5. **Structure-aware chunking** — respect markdown structural boundaries (headers, code blocks, list items)

## Decision

**Adopt fixed-size character chunking with overlap as the v0.1 baseline.**

Parameters:
- `chunk_size = 800` characters (~200 tokens for English technical text)
- `overlap = 100` characters (~25 tokens, ~12% overlap)
- Boundaries: raw character positions — no respect for sentence, paragraph, or structural boundaries

Implementation lives in `src/chunking.py` exposing `chunk_records(records, chunk_size, overlap) -> list[dict]`.

## Rationale

**For fixed-size character chunking specifically.**

- *Simplicity is a feature at v0.1.* A deterministic, dependency-free algorithm produces predictable output. Bad chunking is easier to detect when the algorithm is dumb. Sophisticated chunking strategies obscure their own failures.
- *No external dependencies.* Pure Python — no tokeniser, no NLP library. Faster to install, fewer moving parts to debug.
- *Forms a meaningful baseline.* Phase 6 chunking experiments need something to compete against. A simple deterministic strategy is the right comparison floor.
- *Fast to test.* Module is ~40 lines including docstrings. Can be smoke-tested against the real corpus in minutes.

**For 800 characters / 100 overlap specifically.**

- *800 chars (~200 tokens)* fits inside `text-embedding-3-small`'s 8191-token limit with extreme headroom — zero truncation risk.
- Small enough that 5–10 retrieved chunks fit comfortably inside `gpt-4o`'s prompt budget alongside the question, system prompt, and citation instructions.
- Large enough to carry meaningful content — typically a paragraph or two of technical documentation.
- *100-character overlap (~12%)* preserves sentences and short passages that span chunk boundaries. The most common chunking failure mode is *the answer is split across two chunks and retrieval finds neither* — overlap directly mitigates this.
- These numbers are *starting points, not optima*. Phase 6 will tune them against measured retrieval and answer-quality metrics.

**Against the alternatives, at v0.1.**

- *Token-based chunking* would be more accurate to the embedding model's actual budget but requires a tokeniser dependency. The character-to-token ratio is stable enough for English technical text that characters are an acceptable proxy at v0.1. Phase 6 may revisit if eval results suggest tokens matter.
- *Sentence-aware chunking* requires an NLP library (`nltk` or `spacy`). Disproportionate complexity for v0.1. Phase 6 candidate.
- *Semantic chunking* is computationally expensive (requires embedding sentences twice — once to detect drops, again to build the index). Strong Phase 6 candidate but excessive at v0.1.
- *Structure-aware chunking* (respecting markdown headers, code blocks) is the strongest Phase 6 candidate specifically because the corpus is structured markdown. Deferred to Phase 6 because it requires non-trivial parsing logic that would slow Phase 5 baseline.

## Consequences

**Positive.**

- Phase 5 baseline build proceeds quickly with minimal external dependencies.
- Deterministic output makes failures easier to spot and debug.
- Clean ~40-line module with simple public interface — easy to keep stable while internals evolve.
- Establishes the baseline number against which Phase 6 experiments will be measured.

**Negative.**

- Boundaries will sometimes split sentences and paragraphs awkwardly — expected and accepted at v0.1. Overlap mitigates but does not eliminate.
- Markdown structure (headers, code blocks, tables) is treated as raw text. A code block split mid-line is a known failure mode; logged as a Phase 6 priority.
- Character-based size is a proxy for token-based size; works for English but would fail for languages with very different character-to-token ratios. Acceptable for this corpus (English-only); flagged as a constraint.

**Risk-adjusted view.** This is a known-suboptimal choice made deliberately to ship a baseline. The failure modes are predicted, documented, and queued for Phase 6 resolution. Worst case is Phase 6 measures bad numbers and forces a chunking-strategy revisit — which is exactly what Phase 6 is for.

## Phase 6 experiment queue (deferred work)

Decisions explicitly deferred to Phase 6 with named revisit triggers:

1. **Chunking strategy comparison** — fixed-size character (this baseline) vs structure-aware (markdown-respecting) vs semantic. Triggered by: baseline retrieval recall@k falling below 70% on the golden set.
2. **Chunk size tuning** — sweep `chunk_size` ∈ {400, 800, 1200, 1600} characters against retrieval and answer quality. Triggered by: baseline established, before strategy comparison.
3. **Overlap tuning** — sweep `overlap` ∈ {0%, 12%, 25%, 50%} characters. Triggered by: chunk size locked.
4. **Token-based migration** — replace character counting with token counting via tiktoken. Triggered by: character-based chunks routinely truncating at embedding step (currently zero risk given current parameters).
5. **Hybrid strategies** — structure-aware with size constraints. Triggered by: structure-aware alone outperforming baseline but with chunk-size variance issues.

## Revisit triggers (this ADR)

- **Phase 6 experiments produce a winner.** Update this ADR's status to Superseded, with a forward reference to a new ADR documenting the chosen strategy.
- **New corpus added with different structure.** This ADR is corpus-shape-specific; non-markdown corpora may need different defaults.
- **Embedding model swapped.** A new model with different token budgets or content sensitivity may invalidate the current parameter choices.

## Notes for the playbook

This decision is RAG-specific. Worth noting in `RAG_Solution_Delivery_Playbook.md` §5 step 4 that the recommended v0.1 baseline for new RAG projects is fixed-size character chunking with ~12% overlap, sized to fit comfortably in embedding model and generator prompt budgets. The specific numbers are corpus-dependent; the *shape* of the v0.1 baseline is reusable.