# Phases 1–2 Retrospective — foundry-doc-assistant

| | |
|---|---|
| **Project** | foundry-doc-assistant |
| **Phases covered** | 1 (Discovery & Scoping), 2 (Data & Knowledge Curation) |
| **Time spent** | ~5 hours across W1–W2 |
| **Date** | 2026-05-17 |

## Goal

Establish the project foundation: a clear, defensible problem statement; a reproducible corpus pipeline; a public repo demonstrating both. The deliverable for this stretch wasn't a working RAG system — it was a defensible setup that everything later builds on.

## What we did

**Phase 1 (~2 hrs, W1).**
- Defined the project explicitly as a learning RAG system, dual-purpose (skill-building and portfolio evidence).
- Narrowed corpus scope to Foundry concepts + how-to, excluding API reference. See [ADR 0001](decisions/0001-corpus-scope.md).
- Created public GitHub repo with the README serving as the design doc.
- Wrote predicted failure modes *before* building anything — these now sit as a hostage against future hindsight bias.

**Phase 2 (~3 hrs, W2).**
- Identified `MicrosoftDocs/azure-ai-docs` GitHub repo as the markdown source, rejecting HTML scraping. See [ADR 0002](decisions/0002-corpus-source.md).
- Built a sparse-checkout pipeline limited to `articles/foundry/`.
- Wrote a cleaning pipeline stripping Microsoft markdown extensions while preserving semantic content. See [ADR 0003](decisions/0003-cleaning-approach.md).
- Verified filter math end-to-end: 807 raw markdown files → 376 after path filter → 283 after length filter.
- Committed to a regenerate-not-vendor reproducibility model. See [ADR 0004](decisions/0004-reproducibility-model.md).

## What worked

- **Writing the README as a design doc before code.** Forced explicit decisions about scope, success criteria, and predicted failures. The README ends up doing dual duty as project contract and portfolio piece. Without it, the work would have drifted within a session.
- **GitHub markdown source over HTML scraping.** Cleaner, faster, more stable. The instinct to scrape HTML was abandoned within five minutes once the source repo was identified — that was a good fast pivot.
- **Sparse-checkout.** Limited the fetch to ~MB of relevant markdown instead of the multi-GB full Microsoft docs repo. Made the acquisition reproducible in ~30 seconds, which is cheap enough to run repeatedly without thinking about it.
- **Verifying filter math.** Tracking 807 → 376 → 283 caught the empty `articles/ai-foundry/` directory immediately. Without that sanity check, we'd have shipped a pipeline that quietly indexed half the content we thought it would.

## What surprised us

- **`articles/ai-foundry/` is empty upstream.** Microsoft consolidated everything into `articles/foundry/` via a redirect manifest. Discovered by running the pipeline and finding only a single file in the older path (the redirect JSON). Took ~30 minutes to diagnose and verify the consolidation.
- **Microsoft's docs-specific markdown extensions are richer than expected.** Beyond standard markdown: zone/moniker blocks, image directives, `INCLUDE` transcludes, `<xref:>` cross-references, alert markers. Each required a deliberate semantic decision (strip / replace / preserve).
- **A learning project's Phase 1–3 can collapse into ~5 hours.** Solo, motivated, no stakeholder management — three phases of methodology compressed into two evenings + a weekend morning. This is *not* typical of enterprise work and we shouldn't generalise time estimates from it.

## What we'd do differently

- **Survey the upstream source repo before scoping the acquisition pipeline.** Five minutes of browsing `MicrosoftDocs/azure-ai-docs` at the start of Phase 2 would have surfaced the `ai-foundry/` → `foundry/` consolidation immediately, saving ~30 minutes of diagnosis. **Methodology implication:** Phase 2 should have an explicit upstream-survey step before the acquisition pipeline is designed.
- **Sample 5–10 random records as part of Phase 2 exit.** The 283 records exist, but a quick spot-check of cleaning quality on a handful of random records would catch cleaning bugs early. Currently sitting at Phase 4 entry — should already be done.

## Predictions check (vs Phase 1 failure mode list)

Too early to evaluate the bigger predictions (chunking, LLM-as-judge calibration, hallucinations as retrieval failures, token costs). Those land Phase 4–6. Initial signal on one minor item:

- **Token costs:** Haven't started incurring API costs (no embeddings or generation runs yet). Open.

This section gets revisited at Phase 9.

## Methodology feedback (input to `AI_Delivery_Lifecycle.md` v0.2)

Two patterns from this project that the methodology should capture more explicitly:

1. **Phase 2 should have an upstream-survey step before scoping the acquisition pipeline.** Catching the `ai-foundry/` consolidation 30 minutes earlier would have changed nothing about the eventual answer but improved the path. Add as a key activity.
2. **Phase 2 exit criteria should specify a sample-quality check.** Current methodology says "quality assessment" abstractly; it should specify "spot-check 5–10 random records" as a concrete step. This kind of check is exactly what catches cleaning bugs while they're still cheap to fix.

Both logged in `AI_Delivery_Lifecycle_Observations.md`.

## Open items going into Phase 4

- Brain-dump on the corpus (carry-over, planned Saturday).
- Sample-quality spot-check (carry-over from Phase 2 exit criteria — should be Saturday too).
- Verify Azure OpenAI deployment access for embeddings + GPT-4o.