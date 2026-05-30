"""
Prepare the Foundry corpus for RAG indexing.

Reads markdown files from corpus/source/articles/foundry, resolves Microsoft
docs INCLUDE transclusions by inlining the referenced content, strips
Microsoft docs-specific syntax (zone/moniker blocks, alert markers, image
directives, xrefs), and writes one JSON record per page to
corpus/processed.jsonl.

Each record:
  {
    "id":           short stable hash of source_path
    "source_path":  relative path under corpus/source
    "title":        from frontmatter, falls back to first H1, then filename
    "ms_date":      ms.date from frontmatter (last-revised marker)
    "description":  from frontmatter
    "content":      cleaned markdown body, with INCLUDEs inlined
  }

Run:
    pip install pyyaml
    bash scripts/fetch_corpus.sh
    python scripts/prepare_corpus.py
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterator

import yaml  # pip install pyyaml

SOURCE_ROOT = Path("corpus/source")
OUTPUT_PATH = Path("corpus/processed.jsonl")
INCLUDE_ROOTS = ["articles/foundry"]
MIN_CONTENT_CHARS = 200  # filter out near-empty stubs after cleaning
MAX_INCLUDE_DEPTH = 5    # safety against pathological recursion


# --- Microsoft docs syntax stripping ------------------------------------------
# MS docs use a markdown superset. None of these add semantic content for our
# purposes; stripping them leaves plain markdown the chunker can handle.

# :::zone target="..." pivot="..." ... :::zone-end  (alternative content per pivot)
# Note: MS sometimes authors these with a space — `::: zone` — so we tolerate it.
ZONE_OPEN = re.compile(r":::\s*zone[^\n]*\n", re.MULTILINE)
ZONE_CLOSE = re.compile(r":::\s*zone-end\s*\n?")

# :::moniker range="..." ... :::moniker-end  (content scoped to product versions)
MONIKER_OPEN = re.compile(r":::\s*moniker[^\n]*\n", re.MULTILINE)
MONIKER_CLOSE = re.compile(r":::\s*moniker-end\s*\n?")

# :::row::: / :::column::: / :::column-end::: / :::row-end:::  (layout-only)
ROW_COL = re.compile(r":::\s*(row|column)(-end)?\s*:::[^\n]*\n?")

# :::image type="..." source="..." alt-text="...":::  (with alt text — preserve semantically)
IMAGE_WITH_ALT = re.compile(r":::\s*image[^:]*alt-text=\"([^\"]*)\"[^:]*:::")
# :::image ... :::  (fallback: image without alt-text, e.g. icon/banner images)
IMAGE_NO_ALT = re.compile(r":::\s*image[^:]*:::")

# :::code language="..." source="..." :::  (external code samples — not useful here)
CODE_INCLUDE = re.compile(r":::\s*code[^:]*:::")

# [!NOTE], [!TIP], [!IMPORTANT], [!WARNING], [!CAUTION]  (blockquote callouts)
ALERT = re.compile(r"\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]")

# <xref:something>  -> keep readable text, drop the xref scheme
XREF = re.compile(r"<xref:([^>]+)>")

# YAML frontmatter at the top of every page
FRONTMATTER = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)

# [!INCLUDE [display name](relative/path.md)]  — resolved, not stripped
INCLUDE_DIRECTIVE = re.compile(r"\[!INCLUDE\s*\[[^\]]*\]\(([^)]+)\)\]")

# Safety-net: any unresolved INCLUDE (e.g., file not found) gets stripped
INCLUDE_FALLBACK = re.compile(r"\[!INCLUDE\s*\[[^\]]*\]\([^)]*\)\]")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    match = FRONTMATTER.match(text)
    if not match:
        return {}, text
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    return meta, text[match.end():]


def resolve_includes(text: str, current_file: Path, depth: int = 0) -> str:
    """
    Recursively inline [!INCLUDE [name](path)] references.

    Microsoft docs use INCLUDE heavily to reuse content across pages
    (intros, common steps, sign-in instructions, etc.). Stripping them
    (the v0.1 behaviour) silently lost substantive content because the
    INCLUDE'd material is usually NOT available as a standalone page —
    it's a fragment used only via transclusion.

    This function reads each referenced file relative to the current
    file's location and substitutes its body inline. Recurses to handle
    nested INCLUDEs, capped at MAX_INCLUDE_DEPTH for safety.
    """
    if depth >= MAX_INCLUDE_DEPTH:
        return text

    def replace_one(match: re.Match) -> str:
        relative_path = match.group(1).strip()
        include_path = (current_file.parent / relative_path).resolve()
        try:
            include_raw = include_path.read_text(encoding="utf-8", errors="replace")
        except (FileNotFoundError, OSError):
            return ""  # silently drop unresolvable INCLUDEs
        # Included files occasionally have their own frontmatter; strip it.
        _, include_body = parse_frontmatter(include_raw)
        # Recurse so nested INCLUDEs in the included content also resolve.
        return resolve_includes(include_body, include_path, depth + 1)

    return INCLUDE_DIRECTIVE.sub(replace_one, text)


def strip_ms_syntax(text: str) -> str:
    text = ZONE_CLOSE.sub("", ZONE_OPEN.sub("", text))
    text = MONIKER_CLOSE.sub("", MONIKER_OPEN.sub("", text))
    text = ROW_COL.sub("", text)
    text = IMAGE_WITH_ALT.sub(r"[image: \1]", text)
    text = IMAGE_NO_ALT.sub("[image]", text)
    text = CODE_INCLUDE.sub("[code sample omitted]", text)
    text = ALERT.sub(lambda m: f"{m.group(1).title()}:", text)
    text = INCLUDE_FALLBACK.sub("", text)  # safety net for unresolved INCLUDEs
    text = XREF.sub(r"\1", text)
    # collapse 3+ blank lines back to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def first_h1(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def should_skip(rel_path: Path) -> bool:
    """Skip files that are nav, partial-transclude targets, or pure reference."""
    parts = set(rel_path.parts)
    if "includes" in parts or "breadcrumb" in parts:
        return True
    if rel_path.name in {"TOC.md", "reference.md"}:
        return True
    if rel_path.parent.name == "reference":
        return True
    # API reference docs that live at product folder root with predictable
    # filenames, bypassing the reference/ subfolder filter. See ADR 0008.
    name = rel_path.name
    if name == "latest.md" or name.startswith("reference-") or name.startswith("authoring-reference-"):
        return True
    return False


def iter_records() -> Iterator[dict]:
    for root in INCLUDE_ROOTS:
        for md_path in (SOURCE_ROOT / root).rglob("*.md"):
            rel_path = md_path.relative_to(SOURCE_ROOT)
            if should_skip(rel_path):
                continue
            raw = md_path.read_text(encoding="utf-8", errors="replace")
            meta, body = parse_frontmatter(raw)
            body = resolve_includes(body, md_path)  # NEW: inline INCLUDEs
            content = strip_ms_syntax(body)
            if len(content) < MIN_CONTENT_CHARS:
                continue
            yield {
                "id": hashlib.sha1(str(rel_path).encode()).hexdigest()[:12],
                "source_path": str(rel_path),
                "title": meta.get("title") or first_h1(content) or rel_path.stem,
                "ms_date": str(meta.get("ms.date", "")),
                "description": meta.get("description", ""),
                "content": content,
            }


def main() -> None:
    if not SOURCE_ROOT.exists():
        raise SystemExit(
            f"Source corpus not found at {SOURCE_ROOT}. "
            f"Run scripts/fetch_corpus.sh first."
        )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for record in iter_records():
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    print(f"Wrote {count} records to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()