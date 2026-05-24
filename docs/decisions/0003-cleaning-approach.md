# ADR 0003 — Cleaning approach: strip MS extensions, preserve semantic content

| | |
|---|---|
| **Status** | Superseded by [ADR 0005](0005-cleaning-approach-revised.md) |
| **Date** | 2026-05-17 |
| **Phase** | 2 — Data & Knowledge Curation |

> **Note (added 2026-05-24):** The "drop INCLUDEs because content lives elsewhere" assumption in this ADR was falsified by spot-check evidence in W2-W3. See [ADR 0005](0005-cleaning-approach-revised.md) for the revised approach (INCLUDE resolution by inlining, plus authoring-variance tolerance in directive regexes). This document is retained as historical record.

## Context

Microsoft authors documentation in a markdown superset with several extensions:

- `:::zone target=... pivot=...` ... `:::zone-end` blocks — alternative content per pivot selection
- `:::moniker range=...` ... `:::moniker-end` — content scoped to product versions
- `:::image type=... source=... alt-text=...` directives — image references with alt text
- `:::code language=... source=...` — external code sample includes
- `[!INCLUDE [name](path)]` — transcludes another markdown file
- `[!NOTE]`, `[!TIP]`, `[!WARNING]`, `[!IMPORTANT]`, `[!CAUTION]` — blockquote alert markers
- `<xref:identifier>` — cross-references to other docs

None of these add semantic content the retrieval layer can use; all of them add noise to embeddings if left in. The cleaning step has to decide for each: strip, replace with a semantic equivalent, or leave alone.

## Options considered

1. **Strip everything aggressively.** Drop all MS-specific syntax with no replacement. Risks losing semantic signal: image alt text describes content meaningfully, alert types ("Warning" vs "Note") carry meaning, missing code-sample markers leave a gap where the reader expects context.
2. **Selective stripping with semantic replacement.** Strip syntax tokens but preserve semantic content. Image directives → `[image: alt-text]`. Alert markers → `Note:`, `Tip:`, etc. Code includes → `[code sample omitted]`. INCLUDE transclusions dropped (content lives elsewhere in the corpus, transclusion would create duplicates).
3. **Full transclusion resolution.** Follow `INCLUDE` references and inline their content. Most complete view of each page, but introduces duplication (the same INCLUDE often appears in many pages), creates ordering dependencies, and complicates the pipeline significantly.

## Decision

**Selective stripping with semantic replacement (Option 2).**

Rationale: embeddings benefit from semantic content (alt text describes the image meaningfully); they don't benefit from raw directive syntax. Preserving the meaning while stripping the noise is the right trade-off for retrieval quality.

`INCLUDE` transclusions are dropped specifically because the included content typically appears as a standalone page elsewhere in the corpus. Inlining it would create near-duplicate chunks competing in retrieval, which is worse than not having the content available in context.

## Consequences

- `scripts/prepare_corpus.py` defines explicit regex patterns for each extension with documented intent.
- Edge case: if a piece of content lives *only* in an `INCLUDE` block and never as a standalone page, that content is lost. Verified during Phase 2 quality assessment (filter math: 807 → 376 → 283, with no critical content gaps spotted in the sample).
- Code samples are dropped (`[code sample omitted]`), not pulled in. Eval may show code-related questions are failing.
- Cleaning logic is unit-testable — each regex is independent and deterministic.

### Revisit triggers

- If retrieval consistently misses content that lives only in `INCLUDE` blocks: add a transclusion-resolution pass to the cleaning pipeline. Test by sampling pages that reference `INCLUDE` heavily.
- If eval shows code-context questions failing systematically: extend `:::code` handling to pull in the referenced source file with appropriate language fences.