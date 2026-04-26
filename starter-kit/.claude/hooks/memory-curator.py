"""Memory curator hook for MindMemory — promotes verbatim signals to long-term rules.

Runs as a PostToolUse hook (every N_CURATE tool calls, where N_CURATE > the
collector's interval so the curator sees signals the collector has written).

What it does:
  1. Reads memory/working-memory.md (the "Auto-captured signals" section)
  2. Reads memory/MEMORY.md (existing long-term rules)
  3. Asks Claude (via claude -p) which candidate patterns should promote
  4. Applies a 3-strikes gate (a pattern must be proposed 2+ times before
     it lands in MEMORY.md). State lives in memory/.curator-pending.json.
  5. Caps auto-promotions at 2 per run.
  6. Only APPENDS to MEMORY.md; never rewrites existing entries.
  7. Tags auto-added entries with source frontmatter for auditability.
  8. Writes .last-consolidation.json so session-start-health.py can warn
     if it's been >7 days.

Safety rails:
  - Never touches identity/ files (Tier 1 is sacred).
  - Only archive-moves working-memory entries older than 5 days.
  - Recursion-safe via MINDS_CONSOLIDATING=1.
  - Silent failure — never crashes the parent hook.
  - User can disable by setting MINDS_AUTO_CURATOR=off in env or settings.

MIT — CoMindLab Labs.
"""
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta


# ========== Configuration ==========
INTERVAL = 45                             # fire every N tool calls
MODEL = "sonnet"                          # curation needs judgement; sonnet
MAX_PROMOTIONS_PER_RUN = 2
STRIKES_REQUIRED = 2                      # pattern must be proposed 2+ times
ARCHIVE_STALE_DAYS = 5
TIMEOUT_SECS = 90

PROJECT_ROOT = os.getcwd()
STATE_DIR = os.path.join(PROJECT_ROOT, ".claude")
COUNTER_FILE = os.path.join(STATE_DIR, ".curator-counter")
SESSION_FILE = os.path.join(STATE_DIR, ".curator-session")
LOG_FILE = os.path.join(STATE_DIR, "metrics", "curator-log.txt")

MEMORY_DIR = os.path.join(PROJECT_ROOT, "memory")
WORKING_MEMORY = os.path.join(MEMORY_DIR, "working-memory.md")
LONG_TERM_MEMORY = os.path.join(MEMORY_DIR, "MEMORY.md")
ARCHIVE = os.path.join(MEMORY_DIR, "archive.md")
PENDING_FILE = os.path.join(MEMORY_DIR, ".curator-pending.json")
LAST_RUN_FILE = os.path.join(MEMORY_DIR, ".last-consolidation.json")


CURATOR_PROMPT = """You are a memory curator. You review a developer's working memory (recent signals captured during sessions) and their long-term memory (permanent rules). You propose which candidates should be promoted to long-term.

You will receive:
1. The "Auto-captured signals" section from working-memory.md (recent verbatim user quotes, typed as correction/confirmation/preference)
2. The current MEMORY.md content (what's already permanent)

Your job: identify patterns in the working memory that are:
  - Generalisable (a rule, preference, or recurring mistake — not one-off debug)
  - Recurring (ideally the same theme appears 2+ times)
  - Not already captured in MEMORY.md

Return ONLY JSON (no markdown fences):
{
  "promotions": [
    {
      "title": "short title, slug-friendly",
      "type": "feedback" | "preference" | "project" | "reference",
      "rule": "the rule, in the user's voice where possible",
      "why": "1-line — what evidence led to this (quote a signal if possible)",
      "how_to_apply": "1-line concrete action"
    }
  ]
}

Rules:
  - Be conservative. 0-3 promotions per run is normal. Return empty if nothing strong.
  - Never propose rewriting existing entries — only new ones.
  - Don't propose identity changes (role, personality).
  - If a signal is one-off or ambiguous, skip it.
"""


# ========== Helpers ==========
def _log(msg):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")
    except Exception:
        pass


def _read_hook_input():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def _find_claude_cli():
    for candidate in (
        shutil.which("claude"),
        shutil.which("claude.exe"),
        os.path.expanduser("~/.local/bin/claude.exe"),
        os.path.expanduser("~/.local/bin/claude"),
        r"C:\nodejs\claude.exe",
    ):
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def _read_file_safe(path, default=""):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return default


def _load_json_safe(path, default=None):
    if default is None: default = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json_safe(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".writing"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        shutil.move(tmp, path)
    except Exception as e:
        _log(f"save_json_safe failed: {e}")


def _slugify(title):
    import re
    s = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return s[:60] or "entry"


def _extract_auto_captured_section(working_mem):
    """Return just the ## Auto-captured signals section."""
    marker = "## Auto-captured signals"
    idx = working_mem.find(marker)
    if idx == -1:
        return ""
    # Run until next H2 or end
    rest = working_mem[idx:]
    import re
    next_h2 = re.search(r"\n## [^A]", rest[len(marker):])
    if next_h2:
        return rest[:len(marker) + next_h2.start()]
    return rest


def _call_curator(auto_captured_section, memory_md):
    claude_bin = _find_claude_cli()
    if not claude_bin:
        _log("skipped: no claude CLI")
        return None

    # Truncate if either side is too big
    if len(auto_captured_section) > 8000:
        auto_captured_section = auto_captured_section[-8000:]
    if len(memory_md) > 8000:
        memory_md = memory_md[:8000]

    payload = (
        CURATOR_PROMPT
        + "\n\n---\nAUTO-CAPTURED SIGNALS (working memory):\n"
        + (auto_captured_section or "(empty)")
        + "\n\n---\nCURRENT LONG-TERM MEMORY (MEMORY.md):\n"
        + (memory_md or "(empty)")
    )

    env = os.environ.copy()
    env["MINDS_CONSOLIDATING"] = "1"

    try:
        proc = subprocess.run(
            [claude_bin, "-p", "--model", MODEL, "--output-format", "json"],
            input=payload,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECS,
            env=env,
            creationflags=0x08000000 if sys.platform == "win32" else 0,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        _log("skipped: timeout")
        return None
    except Exception as e:
        _log(f"skipped: exception {e}")
        return None

    if proc.returncode != 0:
        _log(f"skipped: exit={proc.returncode} stderr={proc.stderr[:200]}")
        return None

    try:
        wrapper = json.loads(proc.stdout)
        raw = wrapper.get("result", "").strip()
    except Exception:
        raw = proc.stdout.strip()

    if raw.startswith("```"):
        raw = raw.split("```", 2)[1] if "```" in raw else raw
        if raw.startswith("json"):
            raw = raw[4:].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        _log(f"skipped: invalid JSON: {e} raw={raw[:200]}")
        return None


def _apply_strikes_gate(proposals):
    """Load pending state, match proposals to existing pending items by
    title similarity, return (to_promote_now, to_hold, updated_pending)."""
    pending = _load_json_safe(PENDING_FILE, {})
    now = datetime.now().isoformat()

    promote_now = []
    new_pending = dict(pending)

    for p in proposals:
        title = p.get("title", "").strip()
        if not title: continue
        slug = _slugify(title)

        existing = pending.get(slug)
        if existing:
            existing["strikes"] = existing.get("strikes", 1) + 1
            existing["last_seen"] = now
            existing["latest_rule"] = p
            if existing["strikes"] >= STRIKES_REQUIRED:
                promote_now.append(existing["latest_rule"])
                del new_pending[slug]
            else:
                new_pending[slug] = existing
        else:
            new_pending[slug] = {
                "strikes": 1,
                "first_seen": now,
                "last_seen": now,
                "latest_rule": p,
            }

    # Prune pending items older than 30 days (stale)
    cutoff = (datetime.now() - timedelta(days=30)).isoformat()
    new_pending = {
        k: v for k, v in new_pending.items()
        if v.get("last_seen", "") > cutoff
    }

    return promote_now, new_pending


def _append_to_memory_md(entries):
    """Append promoted entries to MEMORY.md and create individual memory files."""
    if not entries:
        return 0
    os.makedirs(MEMORY_DIR, exist_ok=True)

    # Ensure MEMORY.md exists
    if not os.path.exists(LONG_TERM_MEMORY):
        with open(LONG_TERM_MEMORY, "w", encoding="utf-8") as f:
            f.write("# Memory Index\n\n")

    # Find or create "Auto-curated entries" section
    with open(LONG_TERM_MEMORY, "r", encoding="utf-8") as f:
        content = f.read()
    if "## Auto-curated entries" not in content:
        content += "\n\n## Auto-curated entries\n\n*Added by the memory-curator hook. Review and reorganise at your convenience.*\n\n"

    written = 0
    now_date = datetime.now().strftime("%Y-%m-%d")
    for e in entries[:MAX_PROMOTIONS_PER_RUN]:
        title = e.get("title", "").strip()
        slug = _slugify(title)
        entry_file = f"auto_{slug}.md"
        entry_path = os.path.join(MEMORY_DIR, entry_file)

        # Write individual file
        entry_content = (
            f"---\n"
            f"name: {title}\n"
            f"description: {e.get('why', '')[:200]}\n"
            f"type: {e.get('type', 'feedback')}\n"
            f"source: auto-curator\n"
            f"created: {now_date}\n"
            f"---\n\n"
            f"{e.get('rule', '')}\n\n"
            f"**Why:** {e.get('why', '')}\n"
            f"**How to apply:** {e.get('how_to_apply', '')}\n"
        )
        try:
            # Never overwrite existing file
            if not os.path.exists(entry_path):
                with open(entry_path, "w", encoding="utf-8") as f:
                    f.write(entry_content)

                # Append index line to MEMORY.md
                content += f"- [{title}]({entry_file}) — {e.get('why', '')[:80]} _(auto, {now_date})_\n"
                written += 1
        except Exception as ex:
            _log(f"write_entry_failed: {ex}")

    # Re-write MEMORY.md
    try:
        with open(LONG_TERM_MEMORY, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as ex:
        _log(f"memory_md_write_failed: {ex}")

    return written


def _mark_last_run(stats):
    _save_json_safe(LAST_RUN_FILE, {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "stats": stats,
    })


# ========== Main ==========
def main():
    # Disable switch
    if os.environ.get("MINDS_AUTO_CURATOR", "").lower() == "off":
        sys.exit(0)
    # Recursion guard
    if os.environ.get("MINDS_CONSOLIDATING") == "1":
        sys.exit(0)

    hook_input = _read_hook_input()
    session_id = hook_input.get("session_id", "")

    os.makedirs(STATE_DIR, exist_ok=True)

    # Session change resets counter
    last_session = ""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                last_session = f.read().strip()
        except Exception:
            pass
    if session_id and session_id != last_session:
        try:
            with open(COUNTER_FILE, "w") as f: f.write("0")
            with open(SESSION_FILE, "w") as f: f.write(session_id)
        except Exception:
            pass

    # Increment counter
    count = 0
    try:
        if os.path.exists(COUNTER_FILE):
            with open(COUNTER_FILE, "r") as f:
                count = int(f.read().strip())
    except Exception:
        count = 0
    count += 1
    try:
        with open(COUNTER_FILE, "w") as f:
            f.write(str(count))
    except Exception:
        pass

    if count % INTERVAL != 0:
        sys.exit(0)

    # Only run if there's a memory directory at all
    if not os.path.isdir(MEMORY_DIR):
        _log("skipped: no memory/ dir in project")
        sys.exit(0)

    working = _read_file_safe(WORKING_MEMORY)
    auto_section = _extract_auto_captured_section(working)
    if not auto_section.strip():
        _log("skipped: no auto-captured signals yet")
        sys.exit(0)

    long_term = _read_file_safe(LONG_TERM_MEMORY)

    _log(f"running: session={session_id[:8]} #{count}")
    decision = _call_curator(auto_section, long_term)
    if decision is None:
        sys.exit(0)

    proposals = decision.get("promotions", [])
    if not proposals:
        _log("decision: no promotions proposed")
        _mark_last_run({"proposals": 0, "promoted": 0})
        sys.exit(0)

    promote_now, updated_pending = _apply_strikes_gate(proposals)
    _save_json_safe(PENDING_FILE, updated_pending)

    written = _append_to_memory_md(promote_now) if promote_now else 0
    _log(f"done: proposals={len(proposals)} promoted={written} pending={len(updated_pending)}")
    _mark_last_run({"proposals": len(proposals), "promoted": written, "pending": len(updated_pending)})
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        _log(f"crashed: {e}")
        sys.exit(0)
