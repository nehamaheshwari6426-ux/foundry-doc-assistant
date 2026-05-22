# ADR 0001 — Corpus scope: concepts + how-to only

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-05-17 |
| **Phase** | 1 — Discovery & Scoping |

## Context

The project is a RAG QA system over Microsoft Foundry documentation. The full Foundry doc set is broad — concepts, how-to guides, API/SDK reference, tutorials, architecture guides, responsible AI content.

What gets indexed affects:

- the kinds of questions a golden dataset can credibly answer
- what "good retrieval" means in evaluation
- the cleanliness of the eval signal
- corpus size, embedding cost, and reproducibility friction

Project constraint: this is a learning project at 6–8 hrs/week. The corpus scope has to serve the learning goal — defending RAG decisions with evidence — over corpus realism.

## Options considered

1. **Full Foundry docs.** Broadest and most realistic. Includes API reference content. Cons: reference content (parameter signatures, API tables) rewards keyword search over semantic retrieval and dilutes eval signal. Golden set construction becomes harder because answer correctness for reference-style questions has different shape than for prose.
2. **Concepts + how-to only.** Excludes API reference. Still hundreds of pages of substantive content. Pros: cleaner prose, clearer eval signal, retrieval problems still surface (cross-section synthesis, semantic drift, chunking tradeoffs).
3. **Agents subset.** Small, cohesive. Sets up Project 3 (agentic workflow) narratively. Cons: probably too small to surface real RAG complexity.
4. **Evaluation subset.** Small, with strong narrative tie to Project 2 (eval harness). Same "too small" concern.

## Decision

**Concepts + how-to only.**

Reference content is excluded because it rewards keyword search rather than retrieval over prose — including it degrades both the retrieval evaluation signal and the credibility of any claim about "this chunking strategy improved answers." Concepts and how-to content is the natural domain of RAG, large enough to surface real problems while cohesive enough for a defensible golden set.

## Consequences

- Filter pipeline excludes any path matching `articles/foundry/reference/` and any standalone `reference.md` files.
- Golden set Q/A pairs target conceptual and procedural questions, not API lookups.
- Retrieval eval (recall@k, MRR) measures cross-section understanding, not exact-term matching.
- Anyone reading the project should not expect to use it as an API lookup tool — that's a different system.

### Revisit trigger

If the W6 golden set evaluation surfaces a class of questions consistently failing because users want API references, reconsider whether to add a separate reference-indexed retrieval branch. Don't blend them into the same index — that's the failure mode this decision exists to prevent.