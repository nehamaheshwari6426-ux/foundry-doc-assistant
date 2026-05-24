# Azure AI Foundry Doc Assistant

A retrieval-augmented question-answering system over Azure AI Foundry's conceptual and how-to documentation. Cited answers, measured evals, decisions defended with numbers.

## What this is

This is a learning project, not a product.

The goal is to work through the real decisions in shipping a RAG system end-to-end — chunking strategy, retrieval evaluation, answer evaluation, hallucination handling, cost — and to defend each decision with measured evidence rather than vibes. Every "this works better" claim in this repo will be backed by a golden-set number, or it will be removed.

The system itself is straightforward: ask a natural-language question about Azure AI Foundry, get back a cited answer grounded in Microsoft's public docs.

## Corpus

The **conceptual** and **how-to** content under [Microsoft Foundry documentation](https://learn.microsoft.com/en-us/azure/foundry/), sourced from [`MicrosoftDocs/azure-ai-docs`](https://github.com/MicrosoftDocs/azure-ai-docs).

API reference is deliberately excluded. Reference content gets little uplift from RAG and dilutes eval signal — questions like "what's the signature of X" reward keyword search, not retrieval over prose. Concepts and how-to content is large enough to surface real retrieval problems (hundreds of pages, overlapping topics, mixed prose styles) but cohesive enough to build a defensible golden dataset against.

After cleaning, the corpus is **283 records**. Microsoft recently consolidated the older `articles/ai-foundry/` path into `articles/foundry/`, so the latter is the only active root. The acquisition and cleaning pipeline is fully reproducible — see [Reproduce](#reproduce).

## Architecture (v0.1)

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

Stack, with rationale and revisit triggers:

- **Language**: Python.
- **Embeddings**: Azure OpenAI `text-embedding-3-small`. Cheap, well-supported, fine for general docs prose. *Revisit at W6 — upgrade to `-large` if recall@k disappoints.*
- **Generator**: Azure OpenAI GPT-4o. Same provider as embeddings — one credential, simpler ops. A Claude vs GPT-4o bake-off is genuinely useful but premature without evals to judge it. *Revisit at W7 when golden-set numbers exist.*
- **Vector store**: ChromaDB with local persistence. Trivial setup, clean swap path. pgvector is the upgrade if hosting or scale demands it.
- **Eval harness**: inline through Project 1; extracted as a standalone tool from Project 2 (W13).

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

## Reproduce

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

bash scripts/fetch_corpus.sh

# sparse-checkout of MS Foundry docs
python scripts/prepare_corpus.py  # strip MS syntax → corpus/processed.jsonl

python scripts/inspect_records.py             # 5 random records, side-by-side
python scripts/inspect_records.py -n 50 --seed 1 > logs/brain_dump_records.md
python scripts/inspect_records.py -n 10       # 10 random
python scripts/inspect_records.py --seed 42   # reproducible for shared review
python scripts/inspect_records.py --id abc123 # specific record by id

```

Expected output: ~283 records in `corpus/processed.jsonl`. Corpus content is not committed to this repo (regenerated, not vendored — see `.gitignore`).

## Status

| Week | Done |
|-----:|------|
| W1   | Corpus chosen. Repo and design doc up. |
| W2   | Corpus acquired (283 records). Stack locked. Reproducible pipeline. |
| W3   | Updated scripts and now we have 372 records. |

## Project contains
foundry-doc-assistant/
├── README.md            # updated Sunday with locked stack
├── LICENSE
├── .gitignore           # + corpus/ added
├── pyproject.toml       # or requirements.txt
├── scripts/
│   ├── fetch_corpus.sh  # sparse-checkout of MicrosoftDocs
│   └── prepare_corpus.py # markdown cleaning
└── corpus/              # gitignored — regenerated, not committed
