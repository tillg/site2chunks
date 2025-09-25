#!/usr/bin/env python3
"""
md_to_chunks.py — Markdown → hierarchy-aware chunks → .md files with YAML front matter

- Uses LangChain's MarkdownHeaderTextSplitter to split on headings (H1..H6).
- Uses MarkdownTextSplitter to further chunk long sections without breaking code fences.
- Emits one .md file per chunk with YAML front matter containing useful metadata.

Usage:
  python md_to_chunks.py /path/to/input_dir --out /path/to/output_dir \
      --chunk-size 1200 --chunk-overlap 150 \
      --headers "#,##,###,####,#####,######"
"""

import argparse
import os
import sys
import uuid
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# --- deps ---
try:
    from langchain_text_splitters import (
        MarkdownHeaderTextSplitter,
        MarkdownTextSplitter,
    )
except ImportError:
    print("Missing dependency 'langchain-text-splitters'.\n"
          "Install with: pip install langchain-text-splitters", file=sys.stderr)
    sys.exit(1)


# ---------- utils ----------
SLUG_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")

def slugify(text: str, fallback: str = "chunk") -> str:
    text = text.strip().lower()
    text = text.replace(" ", "-")
    text = SLUG_SAFE.sub("-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or fallback

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ---------- core ----------
def parse_headers_arg(headers_csv: str) -> List[Tuple[str, str]]:
    """
    Convert "#,##,###" → [('#','h1'), ('##','h2'), ('###','h3')]
    """
    headers = []
    for idx, h in enumerate(headers_csv.split(","), start=1):
        h = h.strip()
        if not h:
            continue
        if not set(h) <= {"#"} or len(h) > 6:
            raise ValueError(f"Invalid header token: '{h}' (use only # up to ######)")
        headers.append((h, f"h{len(h)}"))
    return headers


def breadcrumb_from_metadata(md: Dict[str, str], order=("h1","h2","h3","h4","h5","h6")) -> List[str]:
    return [md[k] for k in order if k in md and md[k]]


def chunk_markdown_text(
    text: str,
    headers_to_split_on: List[Tuple[str, str]],
    chunk_size: int,
    chunk_overlap: int,
) -> List[Dict]:
    """
    Returns a list of dict chunks:
      {
        "text": "...",                 # chunk body (no front matter)
        "section_meta": {...},         # header mapping from LC
        "section_breadcrumb": [...],   # ordered breadcrumb titles
        "section_level": int,          # depth (1..6; 0 if no headers)
      }
    """
    # 1) First split by headers to capture hierarchy (breadcrumb lives in metadata)
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,  # keep headings in page_content
    )
    header_docs = header_splitter.split_text(text)

    # 2) For each section, split further with MarkdownTextSplitter (code-fence aware)
    md_splitter = MarkdownTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    out_chunks: List[Dict] = []
    for sect_doc in header_docs:
        sect_text = sect_doc.page_content
        sect_meta = dict(sect_doc.metadata or {})
        breadcrumb = breadcrumb_from_metadata(sect_meta)
        level = len(breadcrumb) if breadcrumb else 0

        sub_chunks = md_splitter.split_text(sect_text)
        for sub in sub_chunks:
            out_chunks.append({
                "text": sub.strip(),
                "section_meta": sect_meta,
                "section_breadcrumb": breadcrumb,
                "section_level": level,
            })
    return out_chunks


def build_front_matter(
    *,
    chunk_id: str,
    source_file: str,
    chunk_index: int,
    total_chunks_in_file: int,
    section_breadcrumb: List[str],
    section_meta: Dict[str, str],
    section_level: int,
    text: str,
    chunk_size: int,
    chunk_overlap: int,
) -> str:
    """
    Returns YAML front matter as a string (without the trailing content).
    """
    fm = {
        "id": chunk_id,
        "created_at": now_iso(),
        "source_file": source_file.replace(os.sep, "/"),
        "chunk_index": chunk_index,
        "total_chunks_in_file": total_chunks_in_file,
        "section_path": section_breadcrumb,             # ordered list of headers
        "section_level": section_level,
        "headers": section_meta,                         # raw header map from LangChain
        "char_count": len(text),
        "splitter": "MarkdownHeaderTextSplitter+MarkdownTextSplitter",
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
    }
    try:
        import yaml  # type: ignore
        fm_yaml = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    except Exception:
        # Lightweight fallback: JSON front matter inside YAML block
        fm_yaml = "json: " + json.dumps(fm, ensure_ascii=False)

    return f"---\n{fm_yaml}\n---\n"


def make_output_name(
    base_path: Path,
    rel_src: Path,
    chunk_index: int,
    breadcrumb: List[str],
) -> Path:
    """
    Make a readable file name like: page-name/h1-h2--chunk-0003.md
    """
    base_no_ext = rel_src.with_suffix("")  # keep directory structure
    # Combine deep title for readability
    title = "-".join([slugify(s) for s in breadcrumb][:4]) or "root"
    fname = f"{title}--chunk-{chunk_index:04d}.md"
    return base_path / base_no_ext / fname


def process_file(
    src_path: Path,
    out_root: Path,
    chunk_size: int,
    chunk_overlap: int,
    headers_to_split_on: List[Tuple[str, str]],
    root_path: Path,
) -> int:
    text = read_text(src_path)
    chunks = chunk_markdown_text(
        text=text,
        headers_to_split_on=headers_to_split_on,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    total = len(chunks)
    rel_src = src_path.relative_to(root_path)

    for idx, ch in enumerate(chunks):
        chunk_id = str(uuid.uuid4())
        fm = build_front_matter(
            chunk_id=chunk_id,
            source_file=str(rel_src),
            chunk_index=idx,
            total_chunks_in_file=total,
            section_breadcrumb=ch["section_breadcrumb"],
            section_meta=ch["section_meta"],
            section_level=ch["section_level"],
            text=ch["text"],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        body = ch["text"]
        content = fm + "\n" + body + "\n"
        out_path = make_output_name(
            base_path=out_root,
            rel_src=rel_src,
            chunk_index=idx,
            breadcrumb=ch["section_breadcrumb"],
        )
        write_text(out_path, content)
    return total


def walk_markdown_files(root: Path) -> List[Path]:
    exts = {".md", ".mdx", ".markdown"}
    return sorted([p for p in root.rglob("*") if p.suffix.lower() in exts])


def main():
    ap = argparse.ArgumentParser(description="Chunk Markdown files into per-chunk .md with YAML front matter.")
    ap.add_argument("input", help="Input file or directory of Markdown files")
    ap.add_argument("--out", required=True, help="Output directory root")
    ap.add_argument("--chunk-size", type=int, default=1200, help="Target chunk size (characters)")
    ap.add_argument("--chunk-overlap", type=int, default=150, help="Character overlap between chunks")
    ap.add_argument("--headers", default="#,##,###,####,#####,######",
                    help="Comma-separated heading levels to split on (e.g. '#,##,###')")
    args = ap.parse_args()

    input_path = Path(args.input).resolve()
    out_root = Path(args.out).resolve()
    ensure_dir(out_root)

    headers_to_split_on = parse_headers_arg(args.headers)

    if input_path.is_file():
        files = [input_path]
        root_path = input_path.parent
    else:
        files = walk_markdown_files(input_path)
        root_path = input_path

    if not files:
        print("No Markdown files found.", file=sys.stderr)
        sys.exit(2)

    total_chunks = 0
    for f in files:
        count = process_file(
            src_path=f,
            out_root=out_root,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            headers_to_split_on=headers_to_split_on,
            root_path=root_path,
        )
        total_chunks += count
        print(f"[OK] {f} → {count} chunks")

    print(f"\nDone. Wrote {total_chunks} chunks into: {out_root}")


if __name__ == "__main__":
    main()