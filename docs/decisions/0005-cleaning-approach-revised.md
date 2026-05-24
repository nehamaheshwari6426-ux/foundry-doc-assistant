# ADR 0005 — Cleaning approach: resolve transclusions, tolerate authoring variance

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-05-24 |
| **Phase** | 2 — Data & Knowledge Curation |
| **Supersedes** | [ADR 0003](0003-cleaning-approach.md) |

## Context

[ADR 0003](0003-cleaning-approach.md) set the original cleaning approach: "Selective stripping with semantic replacement," which included **dropping `[!INCLUDE]` transclusions** on the assumption that included content was available elsewhere in the corpus as standalone pages.

Two evidence cycles in W2 and W3 falsified that assumption and surfaced additional pattern gaps:

**W2 — manual spot-check.** A `Connect to your own storage` page in the corpus showed substantive content missing. The page's intro, sign-in steps, and follow-up sections all lived in `[!INCLUDE]` references that the cleaning pipeline had stripped. The `includes/` directory contained **428 markdown files** — more than the final corpus count of 283 at the time — strongly indicating that INCLUDE content is generally *not* replicated as standalone pages. They exist only as transclusion targets.

**W3 — automated sampling via `inspect_records.py`.** Two cleaning regex gaps surfaced from the first 10-record sample:

- `:::image` directives without `alt-text` attributes leaked through. The original regex required `alt-text` to match, so icon and banner images slipped past cleaning.
- `::: zone` with a space after `:::` (Microsoft authors with both `:::zone` and `::: zone` forms in different files) leaked through. The original regex required no space.

Together, these findings invalidated ADR 0003's INCLUDE assumption and exposed pattern brittleness in the directive regexes.

## Options considered

1. **Resolve INCLUDEs by inlining their content.** Read each referenced file and substitute its body into the parent page. Recurse for nested INCLUDEs. Pros: preserves content as a reader would see it; each cleaned record is whole. Cons: same INCLUDE appears in many parent pages (e.g., common sign-in steps), causing semantic duplication in the index.
2. **Keep INCLUDEs as their own records.** Stop skipping `includes/` directories; emit them as standalone records. Pros: simpler than resolution. Cons: INCLUDEs are usually fragments that don't make sense alone ("Click Create"); retrieval over fragments breaks for synthesis questions; the connection between fragment and parent context is lost.
3. **Hybrid: keep stripping INCLUDEs, accept the content loss as a known limitation.** Document and move on. Pros: zero work. Cons: documented in ADR 0003 already; falsified by the evidence above.

## Decision

**Revised cleaning approach, replacing ADR 0003:**

1. **Resolve INCLUDEs by recursive inlining**, capped at depth 5 to prevent pathological recursion. Read each referenced file relative to the parent page's directory, strip its frontmatter, recursively resolve any nested INCLUDEs, then substitute the result into the parent page. Implemented as `resolve_includes()` in `scripts/prepare_corpus.py`, called from `iter_records()` before `strip_ms_syntax()`.

2. **Tolerate optional whitespace after `:::`** in all directive patterns (zone, moniker, image, code, row, column). Both `:::zone` and `::: zone` now match.

3. **Handle images both with and without alt-text** by splitting into two patterns: `IMAGE_WITH_ALT` normalises to `[image: alt-text]` (preserving semantic content); `IMAGE_NO_ALT` strips to `[image]` (acknowledging the visual without polluting embeddings).

4. **Retain `INCLUDE_FALLBACK` regex as a safety net** for INCLUDEs that fail to resolve (missing files, etc.); these get stripped silently rather than left in the output.

The semantic duplication concern from Option 1 is real but acceptable — common transcluded snippets (sign-in instructions, prerequisites) will appear in multiple records. This biases retrieval slightly toward those snippets but reflects how a reader experiences the docs. Worth measuring at Phase 6, not pre-emptively engineering around.

## Cleaning strategy framework (emerged from this iteration)

The ADR 0003 → ADR 0005 cycle produced a generalisable framework worth codifying:

**Four content categories, each handled differently:**

- **Semantic content** (prose, code, examples) — keep verbatim
- **Semantic metadata** (alt text, alert type, language tags) — keep, normalised
- **Authoring directives** (layout markers, build hints, frontmatter) — strip; readers never see them
- **Cross-references and transclusions** — resolve if target is in corpus; accept loss only if not

**Three-strikes principle for adding any cleaning rule:**

1. **Necessary** — the pattern actually appears in the corpus (don't pre-emptively strip)
2. **Safe** — stripping doesn't change page meaning for a reader
3. **Tested** — a spot-check after applying confirms (1) and (2)

ADR 0003 failed test #2 on INCLUDEs (stripping changed meaning). The original `:::zone` and image regexes failed test #1 (patterns were incomplete). This framework now guides future cleaning rule additions and is being captured in the `AI_Delivery_Lifecycle.md` methodology for v0.2.

## Consequences

- **Corpus size grew from 283 → 373 records** after INCLUDE resolution. Pages that previously fell below the 200-character threshold (because their substantive content was in INCLUDEs) now meet it.
- **`scripts/prepare_corpus.py` is the source of truth** for cleaning behaviour. Future cleaning bug fixes follow the same edit pattern: identify pattern → add/adjust regex → re-run → spot-check → confirm zero leakage.
- **Spot-checking is now non-optional** for Phase 2 exit. Both bug cycles were caught by sampling (manual in W2, scripted via `inspect_records.py` in W3) — not by theoretical review.
- **Cleaning bugs cluster.** Each fix surfaced the next. Logged as a methodology observation: cleaning verification needs to be repeated after every change, not done once.

### Revisit triggers

- **If Phase 6 retrieval evaluation surfaces content gaps** despite the corpus growth, investigate whether some INCLUDE edge case is still mishandled (e.g., INCLUDEs with relative paths that traverse outside the sparse checkout, or `[!INCLUDE]` variants with different syntax).
- **If new MS docs authoring variants appear** in future corpus refreshes, the directive regexes may need further flexibility. Apply the three-strikes principle to any new pattern before adding it.
- **If retrieval bias toward common transcluded snippets** (sign-in steps, prerequisites) becomes a measured problem at Phase 6, consider de-duplication at chunk level or generator-side prompting to ignore boilerplate when answering substantive questions.