"""MindMemory — Memory Index Generator.

Reads structured memory sources (rules + decisions) and writes a single flat
INDEX.md grouped by source type. No LLM, no external deps. Re-run safe — the
index is regenerable; never hand-edit it.

Configuration: reads `config/memory_index.config.json` (relative to repo root)
or accepts --config <path>. Falls back to sensible defaults if missing.

Usage:
    python tools/memory_index_generate.py
    python tools/memory_index_generate.py --config config/memory_index.config.json
    python tools/memory_index_generate.py --dry-run     # print to stdout, do not write

Why no clustering at small N:
    Token-overlap clustering produces one mega-cluster when entries are all
    drawn from a tight domain. Flat sorted lists are honest at <50 entries.
    Clustering is re-introduced when the corpus grows.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Force UTF-8 on stdout/stderr so dry-run prints work on Windows cp1252 consoles.
if sys.platform == "win32":
    for _stream_name in ("stdout", "stderr"):
        _stream = getattr(sys, _stream_name, None)
        if _stream is not None and hasattr(_stream, "buffer"):
            try:
                setattr(sys, _stream_name,
                        io.TextIOWrapper(_stream.buffer, encoding="utf-8",
                                         errors="replace", line_buffering=True))
            except Exception:
                pass

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "memory_index.config.json"

DEFAULT_CONFIG = {
    "rules_dir": "memory/rules",
    "working_memory_file": "memory/working-memory.md",
    "decisions_section": "Key Decisions",
    "output_file": "memory/INDEX.md",
}

DATE_RE = re.compile(r"\((\d{4}-\d{2}-\d{2})\)")


def load_config(path: Path) -> dict:
    if not path.exists():
        return dict(DEFAULT_CONFIG)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"memory_index: invalid config {path}: {e}", file=sys.stderr)
        return dict(DEFAULT_CONFIG)
    merged = dict(DEFAULT_CONFIG)
    merged.update({k: v for k, v in data.items() if v})
    return merged


def resolve(repo_root: Path, rel_or_abs: str) -> Path:
    p = Path(rel_or_abs)
    return p if p.is_absolute() else (repo_root / p)


def extract_rules(rules_dir: Path) -> list[dict]:
    entries = []
    if not rules_dir.exists():
        return entries
    for path in sorted(rules_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        first_heading = ""
        for line in text.splitlines():
            if line.startswith("# "):
                first_heading = line[2:].strip()
                break
        title = first_heading or path.stem.replace("-", " ").title()
        entries.append({
            "kind": "RULE",
            "title": title,
            "source": str(path).replace("\\", "/"),
        })
    return entries


def extract_decisions(working_memory: Path, section_name: str) -> list[dict]:
    entries = []
    if not working_memory.exists():
        return entries
    text = working_memory.read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(
        rf"^###\s+{re.escape(section_name)}\s*$(.+?)^###\s",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(text + "\n### END\n")
    if not m:
        return entries
    block = m.group(1)
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        body = line[2:].strip()
        date_match = DATE_RE.search(body)
        date = date_match.group(1) if date_match else ""
        title = DATE_RE.sub("", body).strip(" —-")
        entries.append({
            "kind": "DECISION",
            "title": title,
            "date": date,
            "source": str(working_memory).replace("\\", "/"),
        })
    return entries


def render_section(out: list[str], heading: str, entries: list[dict],
                   sort_by: str = "title") -> None:
    out.append(f"## {heading} ({len(entries)})")
    out.append("")
    if not entries:
        out.append("_(none)_")
        out.append("")
        return
    if sort_by == "date":
        sorted_entries = sorted(entries, key=lambda e: e.get("date", ""), reverse=True)
    else:
        sorted_entries = sorted(entries, key=lambda e: e["title"].lower())
    for m in sorted_entries:
        line = f"- {m['title']}"
        if m.get("date"):
            line += f" *({m['date']})*"
        line += f" → [{Path(m['source']).name}]({m['source']})"
        out.append(line)
    out.append("")


def build_index(rules: list[dict], decisions: list[dict]) -> str:
    out: list[str] = []
    out.append("# Memory Index")
    out.append("")
    out.append(f"Generated {datetime.now():%Y-%m-%d %H:%M} by `memory_index_generate.py`.")
    out.append("Regenerable — do not hand-edit. Fix sources or tune script instead.")
    out.append("")
    out.append(f"**Sources:** {len(rules)} rules + {len(decisions)} decisions.")
    out.append("")
    out.append("Flat lists for now — auto-clustering re-introduced when entry "
               "count justifies it (~50+).")
    out.append("")
    render_section(out, "Rules", rules, sort_by="title")
    render_section(out, "Decisions (newest first)", decisions, sort_by="date")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="MindMemory index generator")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print INDEX.md to stdout instead of writing")
    args = parser.parse_args()

    cfg = load_config(args.config)
    rules_dir = resolve(args.repo_root, cfg["rules_dir"])
    working_memory = resolve(args.repo_root, cfg["working_memory_file"])
    output_file = resolve(args.repo_root, cfg["output_file"])

    rules = extract_rules(rules_dir)
    decisions = extract_decisions(working_memory, cfg["decisions_section"])

    if not (rules or decisions):
        print("memory_index: no entries extracted — check sources in config",
              file=sys.stderr)
        return 1

    content = build_index(rules, decisions)
    if args.dry_run:
        print(content)
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(content, encoding="utf-8")
    print(f"memory_index: {len(rules)} rules, {len(decisions)} decisions "
          f"{'(dry-run)' if args.dry_run else f'-> {output_file}'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
