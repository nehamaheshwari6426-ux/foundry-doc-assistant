# Next Session Agenda — W5 (or first available)

| | |
|---|---|
| **Drafted** | 2026-05-30 (end of W3 Saturday) |
| **Target session** | W5 Saturday (W4 Saturday confirmed unavailable) |
| **Phase status** | Phase 5 Step 6 complete; Steps 9-12 next |

---

## State at end of W3

Where the project actually is when next session opens.

### Code shipped today

- `src/chunking.py` — fixed-size character chunking, 800/100, tested on real corpus
- `src/embedding.py` — Foundry wrapper with batching, retries, EmbeddingStats observability
- `src/index.py` — ChromaDB persistence layer, cosine distance, upsert by chunk ID
- `scripts/run_chunking.py`, `scripts/run_embedding_smoke.py`, `scripts/build_index.py` — three smoke tests, all passing

### Index actuals (foundry_docs_v1)

- 9,752 chunks indexed
- 1,706,298 tokens consumed
- $0.0341 actual cost (15% under ADR 0009 forecast)
- 9m 27s wall time, zero retries
- Manual retrieval test passing: "What is Microsoft Foundry?" returns 3 semantically relevant chunks with cosine distances 0.19-0.29

### Documentation produced

- ADRs 0006 (version pinning), 0007 (chunking strategy), 0008 (corpus filter refinement), 0009 (cost posture)
- `docs/design/index-module-design-sketch.md`
- `RAG_Solution_Delivery_Playbook.md` v0.1 (in Anthropic project)
- 8+ entries added to `AI_Delivery_Lifecycle_Observations.md`

### What's still pending

- Phase 5 Steps 9-12 (retrieval, generation, response formatting, end-to-end query)
- Phase 4 (golden set with relevance labels)
- First baseline eval against golden set
- AI-103 Module 1 (49 min, due this week regardless of project work)
- LinkedIn post 2 (cost economics topic from today is good source material)

---

## Priorities for next session

Three tiers, in order. Don't move down a tier until the current tier is closed.

### Tier 1 — Phase 5 completion (2.5-3.5 hours)

The end-to-end RAG system has to exist before any meaningful eval is possible. This is the priority.

**1.1 — `src/retrieval.py` (45-60 min)**

Public contract sketch (to be confirmed at session start):

```python
def retrieve(
    query: str,
    k: int = 5,
    collection_name: str = "foundry_docs_v1",
) -> list[dict]:
    """
    Embed the query, search the index, return top-k chunks.

    Returns list of: {id, text, metadata, distance}
    """
```

Design decisions to make at the top of the slot:
- Module imports `embed_texts` from embedding.py and `load_collection` from index.py
- Default k=5 — empirically tuneable later
- Return shape includes distance so caller can decide whether to use weak matches
- No re-ranking at v0.1 (Phase 6 candidate)
- No hybrid search at v0.1 (Phase 6 candidate)

Smoke test: `scripts/run_retrieval.py` — runs 5 sample questions, prints top-k with distances and previews.

**1.2 — `src/generation.py` (60-75 min)**

Most decisions-heavy module of the pipeline. Public contract sketch:

```python
def generate_answer(
    question: str,
    chunks: list[dict],
    model: str = None,  # default from settings
) -> dict:
    """
    Take a question + retrieved chunks, return an answer with citations.

    Returns: {
        answer: str,           # the generated response
        citations: list[dict], # which chunks were cited
        usage: dict,           # tokens in/out, cost
        raw_response: dict,    # full API response for debugging
    }
    """
```

Design decisions to make at session start:
- **Prompt template structure.** System prompt + context block + question block. Specifies "answer ONLY from context; if context insufficient, say so" (per Playbook §5 step 10).
- **Citation format.** Inline markers like `[chunk-id]` or end-of-answer list? Lean toward end-of-answer list with chunk IDs that map back to retrieved chunks for verification.
- **Temperature.** Low (0.0-0.2) for factual Q&A per Playbook §5 step 11.
- **Token budget.** Cap total context tokens (chunks + question + system prompt) at ~6000 to leave headroom in gpt-4o's 128k window. Plenty of slack at v0.1.
- **Output format.** Plain text answer + structured citations list. Don't force JSON output at v0.1.

This module deserves an ADR (10) — prompt design decisions are the kind of choice future-you will second-guess without documentation.

**1.3 — `scripts/run_query.py` (30 min)**

End-to-end wiring. Imports retrieve + generate, takes a question on command line, prints the full answer with citations.

```bash
python scripts/run_query.py "What is Microsoft Foundry?"
```

This is the Phase 5 DoD demonstration: *system runs end-to-end on one question, returns an answer with citations*.

**1.4 — Commit and smoke-test 3-5 questions (15-30 min)**

Run `scripts/run_query.py` against 3-5 of the brain-dump questions. Note observed failure modes (this becomes the Phase 5 retrospective input).

Commit: `Phase 5: retrieval, generation, end-to-end query`.

**End of Tier 1: Phase 5 baseline complete, end-to-end RAG working.**

### Tier 2 — Phase 4 closure (1.5-2 hours)

Phase 4 (Ground Truth & Eval Design) has been hanging — golden set started but incomplete, no relevance labels, no eval harness. Without Phase 4 closed, Phase 6 experiments are running blind.

**2.1 — Brain-dump pass 2 (20 min)**

Add 10-15 more questions to `notes/golden_set_brainstorm.md`. Target categories:
- Synthesis questions (multi-doc reasoning) — under-represented currently
- Comparative questions (X vs Y) — also under-represented
- Edge / gotcha (questions Foundry docs don't fully answer)

Target: 25-30 total questions across all categories.

**2.2 — Relevance labelling (30-45 min)**

For each question in the brain-dump, identify which source records contain the answer. Use the running RAG system from Tier 1 as a *labelling aide* — query each question, see what comes back, manually verify which are correct.

Output format: extend the brain-dump file to include for each question:

```yaml
- question: "What's the difference between Foundry and Azure OpenAI?"
  category: comparative
  expected_sources:
    - articles/foundry/what-is-foundry.md
    - articles/foundry/openai/concepts/...
  expected_chunk_count: 2-4  # rough estimate
  notes: "Answer spans multiple sections; partial answer acceptable."
```

This is the golden set with relevance labels. Phase 4 DoD requirement met.

**2.3 — Minimal eval harness (30-45 min)**

Single script: `scripts/run_eval.py`. Loads golden set, runs each question through retrieval, computes recall@k and MRR against expected_sources. Outputs a markdown report.

Doesn't need to be sophisticated. Doesn't need LLM-as-judge yet. Just *retrieval metrics* against ground truth. The judge work is Project 2 (eval harness as a product).

**End of Tier 2: Phase 4 closed, Phase 5 has measurable baseline.**

### Tier 3 — Non-project (cert + visibility)

Things that have to happen this week regardless of project velocity.

- **AI-103 Module 1 completion** — 49 min remaining, 6 of 9 units left. Thursday slot. Cert track has zero buffer.
- **LinkedIn post 2** — cost economics topic from today. ~30-45 min, any evening.

These belong to weekday evenings, not the Saturday slot.

---

## Decisions queued for top-of-session

Before any coding, confirm these so the slot doesn't lose 30 min to decisions:

1. **Generator model: `gpt-4o` (default per ADR 0002), or experiment with Claude for citation quality comparison?** Recommend stay with gpt-4o for v0.1; ADR-worthy revisit at Phase 6.
2. **Citation format: inline markers `[1] [2]`, or end-of-answer list?** Recommend end-of-answer list, simpler to render, easier to verify against retrieved chunks.
3. **Refusal behaviour: "I don't know" or "the provided context does not contain information about X"?** Recommend the latter — more useful to users and easier to test in evals.
4. **Eval scope at first run: recall@k + MRR only, or also faithfulness via LLM-as-judge?** Recommend retrieval metrics only at first eval; LLM-as-judge is Phase 6 work (calibration alone is half a session).

---

## Anti-goals for next session

Things that must NOT happen, learned from W3 patterns:

- **No methodology work in the project slot.** Methodology v0.2 candidates exist (DoR/DoD restructure, cost economics cross-cutting concern, Phase 5 spot-check pattern). All deferred. Project work only on Saturdays.
- **No new ADRs unless implementation surfaces an actual decision worth recording.** ADR 0010 (generation/prompt design) is likely. Others queue only on real triggers.
- **No scope additions mid-session.** If the build surfaces "we should also do X" — that goes in observations or a TODO, not the current slot's work.
- **Stop at 3 hours regardless of completion state.** Energy management is real.

---

## Pre-session checklist

Things to verify before any coding starts:

- [ ] All today's commits pushed to GitHub (verify with `git log --oneline`)
- [ ] Group 2 files synced to Anthropic project (done today)
- [ ] Index queryable from `load_collection()` — quick sanity check with one query
- [ ] `.env` still gitignored
- [ ] `data/index/` populated (~50-80MB of vectors persisted)
- [ ] Today's brain-dump questions reviewed for synthesis gap

---

## Session structure (rough timeboxing)

If full 3-hour slot available:

| Time | Block | Tier |
|---|---|---|
| 0:00 - 0:10 | Pre-session checklist + decision confirmations | — |
| 0:10 - 1:10 | `src/retrieval.py` + smoke test | Tier 1 |
| 1:10 - 2:25 | `src/generation.py` + ADR 0010 | Tier 1 |
| 2:25 - 2:55 | `scripts/run_query.py` + end-to-end test | Tier 1 |
| 2:55 - 3:00 | Commit, push, stop | — |

If only 2 hours available: drop generation refinement, ship a thin generation that returns "the answer based on these chunks is: {dump}" without prompt sophistication. Adequate for Phase 5 DoD; refine in W6.

If 4+ hours available: add Tier 2 (Phase 4 closure) after Phase 5 completion.

---

## What success at next session looks like

End-of-session check: can I type `python scripts/run_query.py "<question>"` and get back a plausible answer with verifiable citations from the Foundry docs?

If yes: Phase 5 baseline build complete. Phase 6 iteration begins next.

If no: identify which step blocks, commit what works, document the gap, schedule the next slot.