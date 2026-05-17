"""
Prepare the Foundry corpus for RAG indexing.

Reads markdown files from corpus/source/articles/{foundry,ai-foundry},
strips Microsoft docs-specific syntax (zone/moniker blocks, alert markers,
image directives, INCLUDE transcludes, xrefs), and writes one JSON record
per page to corpus/processed.jsonl.

Each record:
  {
    "id":           short stable hash of source_path
    "source_path":  relative path under corpus/source
    "title":        from frontmatter, falls back to first H1, then filename
    "ms_date":      ms.date from frontmatter (last-revised marker)
    "description":  from frontmatter
    "content":      cleaned markdown body
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


# --- Microsoft docs syntax stripping ------------------------------------------
# MS docs use a markdown superset. None of these add semantic content for our
# purposes; stripping them leaves plain markdown the chunker can handle.

# :::zone target="..." pivot="..." ... :::zone-end  (alternative content per pivot)
ZONE_OPEN = re.compile(r":::zone[^\n]*\n", re.MULTILINE)
ZONE_CLOSE = re.compile(r":::zone-end\s*\n?")

# :::moniker range="..." ... :::moniker-end  (content scoped to product versions)
MONIKER_OPEN = re.compile(r":::moniker[^\n]*\n", re.MULTILINE)
MONIKER_CLOSE = re.compile(r":::moniker-end\s*\n?")

# :::row::: / :::column::: / :::column-end::: / :::row-end:::  (layout-only)
ROW_COL = re.compile(r":::(row|column)(-end)?:::[^\n]*\n?")

# :::image type="..." source="..." alt-text="...":::  (replace with alt text)
IMAGE = re.compile(r":::image[^:]*alt-text=\"([^\"]*)\"[^:]*:::")

# :::code language="..." source="..." :::  (external code samples — not useful here)
CODE_INCLUDE = re.compile(r":::code[^:]*:::")

# [!NOTE], [!TIP], [!IMPORTANT], [!WARNING], [!CAUTION]  (blockquote callouts)
ALERT = re.compile(r"\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]")

# [!INCLUDE [name](path)]  (transcludes another file; drop, content lives elsewhere)
INCLUDE = re.compile(r"\[!INCLUDE\s*\[[^\]]*\]\([^)]*\)\]")

# <xref:something>  -> keep readable text, drop the xref scheme
XREF = re.compile(r"<xref:([^>]+)>")

# YAML frontmatter at the top of every page
FRONTMATTER = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    match = FRONTMATTER.match(text)
    if not match:
        return {}, text
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    return meta, text[match.end():]


def strip_ms_syntax(text: str) -> str:
    text = ZONE_CLOSE.sub("", ZONE_OPEN.sub("", text))
    text = MONIKER_CLOSE.sub("", MONIKER_OPEN.sub("", text))
    text = ROW_COL.sub("", text)
    text = IMAGE.sub(r"[image: \1]", text)
    text = CODE_INCLUDE.sub("[code sample omitted]", text)
    text = ALERT.sub(lambda m: f"{m.group(1).title()}:", text)
    text = INCLUDE.sub("", text)
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
    return False


def iter_records() -> Iterator[dict]:
    for root in INCLUDE_ROOTS:
        for md_path in (SOURCE_ROOT / root).rglob("*.md"):
            rel_path = md_path.relative_to(SOURCE_ROOT)
            if should_skip(rel_path):
                continue
            raw = md_path.read_text(encoding="utf-8", errors="replace")
            meta, body = parse_frontmatter(raw)
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