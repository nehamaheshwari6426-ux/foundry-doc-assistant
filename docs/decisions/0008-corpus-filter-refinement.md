# ADR 0008 — Corpus Filter Refinement: Exclude API Reference Docs at Product Root

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-05-30 |
| **Phase** | 5 (Baseline Build) — surfaced by spot-check |
| **Related** | ADR 0001 (Corpus scope), ADR 0005 (Cleaning approach revised) |

## Context

ADR 0001 set the corpus scope as concepts + how-to content only, explicitly excluding API reference for cleaner eval signal. The Phase 2 (W2) implementation in `scripts/prepare_corpus.py` introduced `should_skip()` to enforce this, filtering out:

- Files in `includes/` and `breadcrumb/` directories (navigation, transclusion targets)
- Files named `TOC.md` or `reference.md`
- Files whose parent directory is named `reference/`

This filter caught conventional reference content but missed four large API reference dumps that live at the **root** of product folders rather than in `reference/` subdirectories:

| Source path | Chars | Notes |
|---|---:|---|
| `articles/foundry/openai/latest.md` | 727,990 | v1 REST API reference, misleadingly named |
| `articles/foundry/openai/reference-preview-latest.md` | 543,750 | preview API reference |
| `articles/foundry/openai/reference-preview.md` | 498,728 | preview API reference |
| `articles/foundry/openai/authoring-reference-preview.md` | 242,330 | authoring API reference |

These four documents alone account for ~2 million characters and produce ~3,000 chunks at v0.1 chunk size — roughly **23% of total chunks** in the unfiltered corpus, all of them out of scope per ADR 0001.

The omission was surfaced during Phase 5 baseline spot-check: the diagnostic *"show the 10 largest records by content length"* immediately exposed the four outliers and their path pattern.

## Decision

Extend `should_skip()` in `scripts/prepare_corpus.py` with three additional filename-pattern checks:

```python
# API reference docs that live at product folder root with predictable
# filenames, bypassing the reference/ subfolder filter. See ADR 0008.
name = rel_path.name
if name == "latest.md" or name.startswith("reference-") or name.startswith("authoring-reference-"):
    return True
```

Patterns identified from current corpus inspection:

- `latest.md` — exact match; the v1 REST API reference dump (the name is misleading; this is a reference, not the latest version of content)
- `reference-*` — prefix match; covers `reference-preview.md`, `reference-preview-latest.md`, and any future variants
- `authoring-reference-*` — prefix match; covers the separate authoring API surface

Regenerate `corpus/processed.jsonl` by running `python scripts/prepare_corpus.py`. Expected outcome: ~373 records → ~369 records (4 API reference docs excluded), chunk count drops by ~2,500–3,000.

## Rationale

**Why filename patterns, not size thresholds.** A size-based filter ("skip anything over 200,000 characters") would catch these four documents but also catch legitimate large content like detailed how-to guides. Filtering by *what the document is* (API reference) is more precise than filtering by *how large it is*.

**Why this scope, not broader.** The patterns are deliberately narrow to avoid over-filtering. A broader rule like "skip anything at product folder root" might exclude legitimate landing pages or overviews. The narrow filename patterns catch the known cases; if new patterns emerge during Phase 6 work, this ADR is refined rather than the filter being made arbitrarily aggressive.

**Why surfaced in Phase 5, not Phase 2.** Phase 2's `should_skip()` was designed against Microsoft Docs' *documented conventions* (reference content lives in `reference/` folders). The Foundry corpus had two undocumented conventions the filter didn't anticipate. The Phase 5 baseline spot-check is exactly the safety net for this kind of upstream surprise — the methodology working as intended, even though the initial filter was incomplete.

## Consequences

**Positive.**

- Corpus now matches ADR 0001 scope decision (concepts + how-to only)
- ~23% reduction in chunk count → proportional savings on embedding cost (estimated $0.30–0.50 saved in Phase 5/6 work)
- Retrieval signal cleaner: questions about Foundry concepts won't pull API parameter tables
- Eval signal cleaner: golden set Q&A pairs target the content the system is meant to serve

**Negative.**

- Users asking API-specific questions will get either refusals or weak retrieval; this is correct behaviour for the project's defined scope but a real limitation worth noting
- Filename-pattern filters are brittle if Microsoft renames or restructures; revisit trigger documented below

**Risk-adjusted view.** The cost of *not* fixing this is much higher than the cost of fixing it: every Phase 6 experiment would be measured against a polluted baseline, and every retrieved chunk that came from API reference would degrade answer quality. Caught at Phase 5, this is cheap. Caught at Phase 7, it would require full re-indexing.

## Methodology lesson

The Phase 2 cleaning framework (per ADR 0005) handles the *content* of records well — its four-category model and three-strikes principle are sound. What it didn't anticipate is *what set of records to consider in the first place*. That's a different kind of filtering, and it relies on knowing the corpus's structural conventions ahead of time. The methodology lesson worth banking:

> **The Phase 5 baseline spot-check is the safety net for Phase 2 filtering gaps.** Phase 2 enforces what's known about the corpus structure at curation time. Phase 5 spot-check surfaces what wasn't known. The methodology must include both: upfront filtering against documented conventions, plus systematic spot-checking at baseline against the actual corpus shape.

This applies to RAG projects beyond foundry-doc-assistant. Worth promoting into `RAG_Solution_Delivery_Playbook.md` §5 step 3 (quality assessment) and the playbook's Phase 5 DoD: *"Largest-N spot-check completed; outliers triaged."*

## Revisit triggers

- **Corpus refresh.** If Microsoft restructures `azure-ai-docs`, the filename patterns may stop matching. Re-run the Phase 5 spot-check after each corpus refresh to detect drift.
- **New product folders.** If the corpus expands beyond `articles/foundry/openai/` (e.g., to `articles/foundry/{other-product}/`), spot-check those product folders specifically — they may have their own reference filename conventions.
- **Pattern proliferation.** If the filter accumulates more than ~6 special-case filename patterns, consider promoting to a more general rule (regex pattern, configuration file, or external manifest).

## Related ADR refactor

ADR 0001 (corpus scope) remains accepted; this ADR refines the implementation that fulfils it. No supersession needed — ADR 0001 captured the *intent*, ADR 0008 captures the *complete enforcement*.