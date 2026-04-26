"""Memory collector hook for MindMemory — runs every N tool calls via PostToolUse.

Reads the current session's transcript, detects user corrections, confirmations,
and preferences in the lines since last run, and appends them to
memory/working-memory.md using Claude itself as the curator (via `claude -p`).

Verbatim quotes only — Claude's job is to SELECT what's worth remembering,
not to paraphrase. User audits by reading the file.

Design principles:
- Runs via PostToolUse (not SessionEnd — much more reliable).
- Fires every N tool calls (default 10) so it's cheap.
- Incremental: only processes lines since last run.
- Recursion-safe: refuses to run if MINDS_CONSOLIDATING=1 is set.
- Silent failure: never crashes the calling Claude session.
- Local: no external service, no telemetry. Writes to project memory/ only.

MIT — CoMindLab Labs.
"""
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime


# ========== Configuration ==========
INTERVAL = 10                             # fire every N tool calls
MODEL = "haiku"                           # haiku | sonnet | opus
MAX_TRANSCRIPT_LINES = 80                 # send last N new lines at most
TIMEOUT_SECS = 45

PROJECT_ROOT = os.getcwd()
STATE_DIR = os.path.join(PROJECT_ROOT, ".claude")
COUNTER_FILE = os.path.join(STATE_DIR, ".memory-collector-counter")
SESSION_FILE = os.path.join(STATE_DIR, ".memory-collector-session")
PROGRESS_FILE = os.path.join(STATE_DIR, ".memory-collector-progress.json")
LOG_FILE = os.path.join(STATE_DIR, "metrics", "memory-log.txt")
MEMORY_FILE = os.path.join(PROJECT_ROOT, "memory", "working-memory.md")


# ========== Consolidation prompt (tight, JSON-only output) ==========
CONSOLIDATION_PROMPT = """You are a memory curator for a developer using Claude Code.
You will receive a slice of their recent session transcript.
Identify any user corrections, confirmations, or stated preferences that would be worth remembering next session.

Rules:
1. VERBATIM quotes only. Never paraphrase user words.
2. "Skip" is a valid and preferred answer for routine exchanges.
3. Only select signals that are generalisable — a rule, preference, or recurring mistake. Not one-off debugging details.
4. Small beats large. 0-2 entries is normal. 5+ is suspicious.
5. Ignore the assistant's own messages. Only user messages count.

Output ONLY valid JSON (no markdown fences, no commentary):
{
  "append_to": "working" | "skip",
  "entries": [
    {
      "type": "correction" | "confirmation" | "preference",
      "quote": "exact user words, copied verbatim",
      "context": "1-line what they were correcting/confirming"
    }
  ]
}

If there's nothing worth remembering, return {"append_to": "skip", "entries": []}.
"""


# ========== Helpers ==========
def _log(msg):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")
    except Exception:
        pass  # logging never fails the hook


def _read_hook_input():
    """PostToolUse hook receives JSON on stdin."""
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def _find_transcript(session_id):
    """Find the JSONL transcript file for this session_id."""
    if not session_id:
        return None
    trans_dir = os.path.expanduser("~/.claude/projects")
    if not os.path.isdir(trans_dir):
        return None
    for root, _, files in os.walk(trans_dir):
        for f in files:
            if f.startswith(session_id) and f.endswith(".jsonl"):
                return os.path.join(root, f)
    return None


def _load_progress():
    if not os.path.exists(PROGRESS_FILE):
        return {}
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_progress(progress):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress, f, indent=2)
    except Exception:
        pass


def _get_new_user_messages(transcript_path, last_line):
    """Yield user messages from lines after last_line in the transcript.
    Returns (new_messages, new_last_line_count)."""
    messages = []
    line_count = 0
    with open(transcript_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line_count = i + 1
            if i < last_line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") != "user":
                continue
            content = obj.get("message", {}).get("content", "")
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = " ".join(
                    b.get("text", "") for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            else:
                text = ""
            text = text.strip()
            if text and not text.startswith("<system-reminder>"):
                ts = obj.get("message", {}).get("timestamp") or obj.get("timestamp", "")
                messages.append({"text": text[:1000], "ts": ts})
    return messages, line_count


def _find_claude_cli():
    """Locate claude.exe / claude on PATH or in common locations."""
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


def _call_consolidator(messages):
    """Send messages to claude -p, get back JSON curation decision."""
    claude_bin = _find_claude_cli()
    if not claude_bin:
        _log("skipped: claude CLI not found on PATH")
        return None

    user_payload = "\n\n".join(
        f"[{m['ts'][:19] if m['ts'] else '?'}] USER: {m['text']}" for m in messages
    )
    full_prompt = CONSOLIDATION_PROMPT + "\n\n---\nRecent user messages:\n" + user_payload

    env = os.environ.copy()
    env["MINDS_CONSOLIDATING"] = "1"  # recursion guard

    # Pass prompt via stdin to avoid Windows argv length limit (~8KB).
    # --input-format text makes claude -p read stdin as the user prompt.
    try:
        proc = subprocess.run(
            [claude_bin, "-p", "--model", MODEL, "--output-format", "json"],
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECS,
            env=env,
            creationflags=0x08000000 if sys.platform == "win32" else 0,  # CREATE_NO_WINDOW
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        _log(f"skipped: claude -p timed out after {TIMEOUT_SECS}s")
        return None
    except Exception as e:
        _log(f"skipped: claude -p failed: {e}")
        return None

    if proc.returncode != 0:
        _log(f"skipped: claude -p exit={proc.returncode} stderr={proc.stderr[:200]}")
        return None

    # claude -p --output-format json returns a wrapper; the actual model output is in .result
    try:
        wrapper = json.loads(proc.stdout)
        result_text = wrapper.get("result", "").strip()
    except Exception:
        result_text = proc.stdout.strip()

    # strip any accidental markdown fences
    if result_text.startswith("```"):
        result_text = result_text.split("```", 2)[1] if "```" in result_text else result_text
        if result_text.startswith("json"):
            result_text = result_text[4:].strip()

    try:
        decision = json.loads(result_text)
    except json.JSONDecodeError as e:
        _log(f"skipped: consolidator returned invalid JSON: {e} raw={result_text[:200]}")
        return None

    return decision


def _append_to_working_memory(entries, session_id):
    if not entries:
        return 0
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)

    now = datetime.now()
    date_heading = now.strftime("%Y-%m-%d")
    time_stamp = now.strftime("%H:%M")
    session_tag = (session_id or "unknown")[:8]

    # Compose the block
    lines = [""]
    # Find-or-create the "Auto-captured signals" section. For simplicity,
    # just append — user can reorganise by hand.
    lines.append(f"### {date_heading} {time_stamp} — session {session_tag}")
    for e in entries:
        etype = e.get("type", "note")
        quote = e.get("quote", "").replace("\n", " ").strip()[:300]
        ctx = e.get("context", "").strip()[:200]
        if not quote:
            continue
        lines.append(f"- [{etype}] \"{quote}\"" + (f" — {ctx}" if ctx else ""))
    lines.append("")

    block = "\n".join(lines)

    # Ensure the file has the Auto-captured section header
    needs_header = True
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            existing = f.read()
        if "## Auto-captured signals" in existing:
            needs_header = False

    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        if needs_header:
            f.write("\n## Auto-captured signals\n\n*Verbatim quotes selected by the memory-collector hook. Curate into MEMORY.md or delete.*\n")
        f.write(block)

    return len(entries)


# ========== Main ==========
def main():
    # Recursion guard: refuse to run inside a spawned claude -p call
    if os.environ.get("MINDS_CONSOLIDATING") == "1":
        sys.exit(0)

    hook_input = _read_hook_input()
    session_id = hook_input.get("session_id", "")

    # Session-change detection: reset counter if new session
    os.makedirs(STATE_DIR, exist_ok=True)
    last_session = ""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                last_session = f.read().strip()
        except Exception:
            pass

    if session_id and session_id != last_session:
        try:
            with open(COUNTER_FILE, "w") as f:
                f.write("0")
            with open(SESSION_FILE, "w") as f:
                f.write(session_id)
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

    # Fire only every INTERVAL tool calls
    if count % INTERVAL != 0:
        sys.exit(0)

    # Find transcript
    transcript = _find_transcript(session_id)
    if not transcript:
        _log(f"skipped: no transcript for session {session_id[:8]}")
        sys.exit(0)

    # Resume from last processed line
    progress = _load_progress()
    last_line = progress.get(session_id, 0)

    try:
        messages, new_last_line = _get_new_user_messages(transcript, last_line)
    except Exception as e:
        _log(f"skipped: failed to read transcript: {e}")
        sys.exit(0)

    # Trim to reasonable size
    if len(messages) > MAX_TRANSCRIPT_LINES:
        messages = messages[-MAX_TRANSCRIPT_LINES:]

    if not messages:
        # Still update progress so we don't re-scan
        progress[session_id] = new_last_line
        _save_progress(progress)
        sys.exit(0)

    _log(f"running: session={session_id[:8]} tool_call#{count} msgs={len(messages)}")

    decision = _call_consolidator(messages)
    if decision is None:
        # Consolidator failed — don't advance progress so we retry next cycle
        sys.exit(0)

    entries = decision.get("entries", [])
    append_to = decision.get("append_to", "skip")

    written = 0
    if append_to == "working" and entries:
        written = _append_to_working_memory(entries, session_id)

    _log(f"done: decision={append_to} entries={len(entries)} written={written}")

    # Advance progress
    progress[session_id] = new_last_line
    _save_progress(progress)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        _log(f"crashed: {e}")
        sys.exit(0)  # never fail the parent hook
