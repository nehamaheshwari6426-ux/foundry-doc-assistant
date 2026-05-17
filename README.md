# Azure AI Foundry Doc Assistant

A retrieval-augmented question-answering system over Azure AI Foundry's conceptual and how-to documentation. Cited answers, measured evals, decisions defended with numbers.

## What this is

This is a learning project, not a product.

The goal is to work through the real decisions in shipping a RAG system end-to-end — chunking strategy, retrieval evaluation, answer evaluation, hallucination handling, cost — and to defend each decision with measured evidence rather than vibes. Every "this works better" claim in this repo will be backed by a golden-set number, or it will be removed.

The system itself is straightforward: ask a natural-language question about Azure AI Foundry, get back a cited answer grounded in Microsoft's public docs.

## Corpus

The **conceptual** and **how-to** sections of the [Azure AI Foundry documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/).

API reference is deliberately excluded. Reference content gets little uplift from RAG and dilutes eval signal — questions like "what's the signature of X" reward keyword search, not retrieval over prose. Concepts and how-to content is large enough to surface real retrieval problems (hundreds of pages, overlapping topics, mixed prose styles) but cohesive enough to build a defensible golden dataset against.

## Architecture (v0.1 — finalised W2)

```
question
   │
   ▼
embedder ──► vector store ──► top-k chunks
                                  │
                                  ▼
                          generator + prompt
                                  │
                                  ▼
                         answer + citations
                                  │
                                  ▼
                                 eval
```

Planned stack:

- **Language**: Python
- **Embeddings**: Azure OpenAI `text-embedding-3-small` (default; `-large` if recall demands it)
- **Generator**: Claude or GPT-4o — picked in W2 on a small cost/quality bake-off
- **Vector store**: ChromaDB locally, pgvector if hosting forces a change
- **Eval harness**: starts inline here, extracted into a standalone tool from month 4

## Evaluation approach

Two evals, introduced from W6:

1. **Retrieval eval** — recall@k and MRR against a hand-built golden set of 30–50 question/chunk pairs spanning easy/hard and factual/interpretive.
2. **Answer eval** — LLM-as-judge for faithfulness (is the answer grounded in retrieved chunks?) and completeness. Calibrated against ~20 human-labelled examples before being trusted.

Cost and latency tracked alongside quality once the harness lands. Statistical confidence on small golden sets, not just averages.

## Roadmap

Twelve weeks, roughly 6–8 hours per week.

| Weeks | Focus |
|------:|-------|
| 1–4   | Corpus, stack, v0.1 pipeline, golden dataset |
| 5–8   | First measured evals; compare chunking strategies |
| 9–12  | Citations, hallucination check, hosted demo, write-up |

## What I expect to fail at

Honest predictions, written before the data lands, so they can be checked later:

- **Chunking will matter more than feels reasonable.** Fixed-size will under-perform on cross-section questions. Semantic chunking will work but be fiddly to tune. Hybrid will probably win on numbers and lose on simplicity.
- **LLM-as-judge will disagree with me about completeness.** Faithfulness will calibrate easily; completeness will not. I'll need labelled disagreement data before trusting the score.
- **Most "hallucinations" will turn out to be retrieval failures.** The generator will dutifully answer from missing context. The fix won't be a better prompt; it'll be better retrieval.
- **Token costs will surprise me.** They always do.

This list gets updated as reality lands, not quietly deleted.

## Status

| Week | Done |
|-----:|------|
| W1   | Corpus chosen. Repo and design doc up. |
