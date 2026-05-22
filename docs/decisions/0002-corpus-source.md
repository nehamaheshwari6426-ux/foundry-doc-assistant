# ADR 0002 — Corpus source: GitHub markdown, not scraped HTML

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-05-17 |
| **Phase** | 2 — Data & Knowledge Curation |

## Context

Microsoft publishes the Azure AI Foundry documentation in two forms:

- **Rendered HTML** on `learn.microsoft.com` — the user-facing site
- **Authoring markdown source** in the public GitHub repo `MicrosoftDocs/azure-ai-docs`

Both contain the same content but require very different acquisition pipelines, with different reproducibility, brittleness, and cleaning trade-offs.

## Options considered

1. **Scrape HTML from `learn.microsoft.com`.** Standard approach using BeautifulSoup or similar. Cons: brittle (page templates change), needs robots.txt compliance, slower, includes navigation chrome that must be stripped, hard to verify reproducibility (HTML can change between fetches with no version anchor), licensing/attribution model is murkier when scraping rendered pages.
2. **Clone GitHub markdown source.** Plain markdown, version-controlled by upstream, syntax is stable and documented. `git sparse-checkout` limits the fetch to the relevant subtree. Reproducibility built in via git refs. Microsoft's docs-specific markdown extensions (zone/moniker blocks, image directives) are well-documented and can be handled deliberately. Licensing is explicit (CC BY 4.0 for content, MIT for code samples).
3. **Microsoft Learn API.** Not publicly available for general doc retrieval at the level needed.

## Decision

**Clone the GitHub markdown source via sparse-checkout.**

The acquisition pipeline becomes a 10-line shell script. Reproducibility is a property of git, not something we have to engineer. The cleaning problem shifts from "parse possibly-changing HTML and strip rendering artifacts" to "strip a known, documented set of MS markdown extensions" — a much smaller, well-defined problem with deterministic regex-level solutions.

## Consequences

- `scripts/fetch_corpus.sh` uses `git clone --depth 1 --filter=blob:none --sparse`, then `git sparse-checkout set articles/foundry`.
- The cleaning step (`scripts/prepare_corpus.py`) handles Microsoft markdown extensions, not HTML.
- Licensing/attribution captured: Microsoft docs are CC BY 4.0 (content) and MIT (code samples). Project README notes the source repo and licence.
- If `MicrosoftDocs/azure-ai-docs` reorganises or is deprecated, the pipeline breaks until the path mapping is updated.

### Revisit trigger

If a future project needs content not in `MicrosoftDocs/azure-ai-docs` (e.g., third-party docs or rendered-only content like Confluence), revisit the scraping approach for that specific corpus. Don't generalise this decision — it's source-specific.