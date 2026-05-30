# ADR 0009 — Cost Posture: Learning Project, Negligible-Cost Assumption

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-05-30 |
| **Phase** | 5 (Baseline Build) — surfaced when embedding module measured first API costs |
| **Related** | ADR 0002 (Stack selection), RAG Solution Delivery Playbook §3 (Phase 0 decisions) |

## Context

The Phase 5 embedding module surfaced the first real API costs in foundry-doc-assistant: $0.036 estimated for full-corpus indexing, measured via a 10-chunk smoke test extrapolating to 9,752 chunks. Until this point, costs were implicitly assumed negligible — a reasonable assumption for a learning project, but assumed rather than documented.

The playbook's Phase 0 §3.6 (Scope and sequencing) calls for cost budget commitments before building. ADR 0001 framed this as a learning project but did not document explicit cost assumptions. This ADR closes that gap retroactively, anchoring all subsequent cost decisions to a named posture.

## Decision

**Adopt a "learning project, negligible-cost" posture for foundry-doc-assistant** through Phase 8 deployment, with the following explicit commitments:

**Cost ceiling.** Total project API spend across Phase 5–9 budgeted at AUD $20 (≈USD $13). Includes embedding generation, query inference for evals, Phase 6 experimentation, and one re-index. Threshold for "stop and re-evaluate" rather than hard limit.

**Per-query cost target.** Not formally constrained at v0.1. Phase 6 iteration may surface a target if eval results suggest cost-quality tradeoffs. Estimated current state: <$0.005 per query (one embedding + one generation), measured at first end-to-end run.

**Cost monitoring.** `EmbeddingStats` dataclass already in place for embedding observability. Generation module (forthcoming) will follow the same pattern. Phase 5 DoD informally extended: each module's smoke test reports cost actuals.

**Cost-vs-quality philosophy.** Quality first, cost second, but cost measured throughout. The learning value of building rigorous evaluation and quality controls outweighs marginal API spend at this scale. If cost approaches the ceiling, the response is investigation (why is it high?), not premature optimisation.

**Approval chain for overruns.** Self-approved up to AUD $50 total spend. Beyond that, pause for explicit reconsideration of whether the project shape still serves Year 1 goals.

**Eval running budget.** Folded into the overall ceiling. Golden-set evaluation with LLM-as-judge expected to be the largest single line item once Phase 4 lands. Forecast: ~$1–3 per full golden-set run, depending on judge model choice.

**One-time vs recurring framing.** This is fundamentally a one-time-cost project — there's no production query load. Recurring costs (re-indexing on corpus refresh, re-running evals as the system evolves) are bounded and predictable, not user-volume-driven.

## Rationale

**Why now, not Phase 0.** ADR 0001 was right to defer detailed cost commitments until real measurements existed — guessing at costs before any API calls would have produced numbers with no basis. The first embedding API call gave the first real cost signal. Documenting the posture *immediately after* first measurement is the right cadence for a learning project; for client work, the posture would be committed up front with assumed ranges.

**Why a ceiling, not just a target.** Ceilings catch surprises; targets only guide. Without a ceiling, Phase 6 experiments could quietly compound — an enthusiastic chunking-strategy sweep could easily run 5–10x baseline indexing cost. The ceiling forces an explicit "is this still in scope?" decision rather than silent overrun.

**Why AUD $20.** Round, generous, defensible. Estimated full project spend: indexing ($0.04), Phase 6 experiments at 5x baseline ($0.20), golden-set evals at 10 runs ($30 at $3 each — oh wait, that's the budget). The math is rough; this is a number to anchor against, not a precise forecast.

Adjusting: golden-set evals are the dominant line item once they start. Real forecast: indexing ($0.04) + experimentation ($0.20) + 6 eval runs at $1–3 each ($6–$18). Total realistic spend: $6–$18. AUD $20 ceiling provides ~10% headroom.

**Why quality first.** A learning project optimising for cost over quality produces inferior portfolio evidence and weak methodology learnings. The whole point of Year 1 is to build credibility for AI delivery, not to ship cheap RAG demos. Cost discipline is a methodology *practice*, not the project's *goal*.

## Consequences

**Positive.**

- Cost assumptions now explicit and auditable
- Phase 6 experiments have a named ceiling, preventing silent compounding
- Observability work (`EmbeddingStats`) gains a purpose — measuring against a documented budget
- Methodology IP gains a concrete example of cost-posture documentation for the eventual v0.2 playbook update
- Future client conversations can reference this as a worked example of project-appropriate cost discipline

**Negative.**

- AUD $20 ceiling is an estimate; if golden-set evals run more times or use larger judge models, may need re-evaluation. Documented as a revisit trigger below.
- No per-query target means Phase 6 cost-quality tradeoffs lack a hard anchor. Acceptable at v0.1 (learning project); deficient for client work.

**Risk-adjusted view.** This is appropriate cost discipline for a learning project of this scope. The numbers are small enough that precision doesn't matter; what matters is the *practice* of naming the posture explicitly. Same practice scales to six-figure cost commitments for enterprise work — just with more decimal places.

## Revisit triggers

- **Eval cost exceeds $5 per run.** May indicate judge model is too large or golden set has grown beyond intended size. Re-evaluate eval cost economics before scaling up eval frequency.
- **Phase 6 cumulative experiment spend exceeds $5.** Indicates either bad experiment design (running too many variants) or unexpectedly expensive operations (cross-encoder reranking experiments are real money). Trigger for batching experiments differently.
- **Total spend reaches AUD $15 (75% of ceiling).** Pause for explicit re-budget conversation rather than waiting until ceiling is breached.
- **Project scope expands beyond learning project.** If foundry-doc-assistant becomes part of a paid engagement or production deployment, this ADR is superseded by a full cost-contract ADR with per-query targets, monthly budgets, and SLA commitments.

## Methodology lesson

The pattern surfaced here belongs in the playbook v0.2 as a fifth cross-cutting concern. Cost economics weave through every phase — Phase 0 commits, Phase 3 architecture decisions lock in trajectory, Phase 5 measures baseline, Phase 6 iterates with cost as a metric, Phase 7 hardens controls, Phase 8 forecasts operations, Phase 9 reconciles. Deferring all cost thinking to Phase 7 is the antipattern, in the same shape as deferring regulatory thinking.

The methodology gap was: cost decisions weren't given the same explicit structural treatment as quality, governance, and evaluation. Filed as a v0.2 playbook restructure candidate in `AI_Delivery_Lifecycle_Observations.md` entry of the same date.

## Related ADR refactor

ADR 0001 (project scope) implicitly assumed negligible cost; this ADR makes that assumption explicit and bounded. No supersession needed — ADR 0001 captured the scope intent, ADR 0009 captures the cost intent.