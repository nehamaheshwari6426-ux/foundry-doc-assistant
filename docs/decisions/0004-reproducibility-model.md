# ADR 0004 — Reproducibility model: regenerate corpus, never vendor

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-05-17 |
| **Phase** | 2 — Data & Knowledge Curation |

## Context

The cleaned corpus is 372 records totalling ~few MB. It would fit in a Git repo without strain.

The question is whether to commit `corpus/processed.jsonl` directly to the repo (vendoring) or treat it as a build artifact regenerated from the cleaning scripts (reproducibility). This is the kind of decision that's quietly consequential — it shapes how trustworthy "I ran the pipeline" claims are six months later.

## Options considered

1. **Vendor the cleaned corpus.** Commit `corpus/processed.jsonl` to the repo. Pros: anyone cloning the repo has the corpus immediately, no setup step. Cons: every change to the cleaning logic requires a recommit; the committed corpus drifts from the upstream source over time (Microsoft updates docs constantly); provenance is lost (which commit of cleaning logic produced this file?); repo size grows with every regeneration.
2. **Regenerate the corpus from scripts.** Commit only `scripts/fetch_corpus.sh` and `scripts/prepare_corpus.py`. Add `corpus/` to `.gitignore`. Anyone cloning the repo runs the two scripts to regenerate. Pros: cleaning logic is the source of truth; corpus always matches the current scripts; upstream changes pick up automatically; repo stays small. Cons: extra setup step (~30 seconds + a few seconds for cleaning).
3. **Hybrid: vendor a snapshot, regenerate for active development.** Commit a tagged corpus snapshot for reproducibility of past results; regenerate for current work. Cons: adds complexity, and the snapshot-vs-regenerated divergence is exactly the bug we're trying to avoid.

## Decision

**Regenerate the corpus from scripts; never vendor. Add `corpus/` to `.gitignore`.**

The cleaning pipeline is the source of truth, not the cleaned output. Vendoring makes it possible — and over time likely — for the committed corpus to drift from what the scripts would produce, silently breaking reproducibility. The extra setup step is small and aligns with the methodology principle that every artifact regenerates from a documented command.

## Consequences

- `.gitignore` excludes `corpus/`.
- README's "Reproduce" section documents the two-command regeneration: `./scripts/fetch_corpus.sh && python scripts/prepare_corpus.py`.
- Microsoft docs licensing (CC BY 4.0) is honoured — content isn't redistributed via the repo, only the regeneration pipeline is.
- If `MicrosoftDocs/azure-ai-docs` changes upstream, the corpus changes too. This is correct behaviour, but means evaluation runs need to capture the corpus state at the time (date or upstream git ref) for true reproducibility of past results.

### Revisit triggers

- **If the project ever ships a hosted demo:** the demo deployment needs either a corpus snapshot baked into the image or the ability to fetch at deploy-time. Decide then.
- **If retrospective evaluation of past results becomes important** (e.g., comparing W4 baseline numbers against W12 final numbers): start capturing the upstream commit SHA in each eval run's metadata so the corpus at any past point can be reconstructed.