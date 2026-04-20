"""Session metrics collector for Minds — measures whether memory helps you.

Parses the Claude Code JSONL transcript from the most recent session and
extracts:

- Productivity: tool calls split into exploration vs productive
- Orientation: how many exploration calls before the first productive edit
- Memory state: whether memory/working-memory.md was loaded
- Emotional signals: negative/positive language, repeated corrections
- Identity: whether a mind greeting fired (detection is generic — any
  "Hi, I'm <Name>." or "<Name>:" opening will be picked up)

Outputs to .claude/metrics/session-metrics.csv.

Invoked via SessionEnd hook. Can also be run standalone for ad-hoc analysis
of the most recent transcript.

Generic — no hard-coded mind names. Works for any mind the user defines via
/mind-setup. MIT — CoMindLab Labs.
"""
import csv
import glob
import json
import os
import re
import sys
from datetime import datetime


METRICS_DIR = os.path.join(os.getcwd(), ".claude", "metrics")
METRICS_FILE = os.path.join(METRICS_DIR, "session-metrics.csv")
TRANSCRIPTS_DIR = os.path.expanduser("~/.claude/projects")


EXPLORATION_TOOLS = {"Read", "Grep", "Glob", "Agent", "ToolSearch", "WebSearch", "WebFetch"}
PRODUCTIVE_TOOLS = {"Edit", "Write", "NotebookEdit"}
META_TOOLS = {"TodoWrite", "Skill", "AskUserQuestion", "EnterPlanMode", "ExitPlanMode"}


CSV_HEADERS = [
    "timestamp",
    "session_id",
    "project_dir",
    "duration_minutes",
    "total_tool_calls",
    "exploration_calls",
    "productive_calls",
    "bash_calls",
    "meta_calls",
    "agent_calls",
    "first_edit_index",
    "exploration_before_first_edit",
    "working_memory_tokens",
    "memory_loaded",
    "negative_signals",
    "positive_signals",
    "strong_negative",
    "repeated_corrections",
    "mind_name",
    "greeted_as_mind",
    "identity_anchor_fired",
]


NEGATIVE_SIGNALS = [
    "no,", "no!", "wrong", "that's not", "that is not", "not what i asked",
    "stop doing", "don't do that", "don't do this", "i said", "again?",
    "ugh", "argh", "ffs",
    "not right", "incorrect", "missed the point", "misunderstood",
    "you keep", "you're doing it again", "as i said", "told you",
]
POSITIVE_SIGNALS = [
    "nice", "perfect", "exactly", "exactly that", "well done", "great",
    "nailed it", "this is it", "yes!", "that's right", "spot on",
    "brilliant", "love it", "keep doing that", "that's what i wanted",
]
STRONG_NEGATIVE = ["fuck", "shit", "wtf", "damn it"]


# Generic mind greeting detection. Matches either:
#   - "Hi, I'm <Name>." anywhere in first 200 chars of first assistant message
#   - "<Name>:" as the very first token (hook-enforced first-word pattern)
# Extracts the name via regex so no hard-coded mind list is needed.
GREETING_INTRO = re.compile(r"hi,?\s+i(?:'|’)m\s+([a-z][a-z0-9_-]{1,30})\b", re.IGNORECASE)
GREETING_PREFIX = re.compile(r"^\s*([a-z][a-z0-9_-]{1,30}):\s", re.IGNORECASE)


def find_latest_transcript():
    """Find the most recently modified .jsonl transcript across all projects."""
    if not os.path.isdir(TRANSCRIPTS_DIR):
        return None

    latest = None
    latest_mtime = 0
    for root, _, files in os.walk(TRANSCRIPTS_DIR):
        for f in files:
            if f.endswith(".jsonl"):
                p = os.path.join(root, f)
                try:
                    mt = os.path.getmtime(p)
                except OSError:
                    continue
                if mt > latest_mtime:
                    latest_mtime = mt
                    latest = p
    return latest


def parse_transcript(jsonl_path):
    tool_calls = []
    first_timestamp = None
    last_timestamp = None
    working_memory_tokens = 0
    memory_loaded = False

    neg_count = 0
    pos_count = 0
    strong_neg = False
    repeated_corrections = 0
    correction_topic_counts = {}

    mind_name = ""
    greeted_as_mind = False
    identity_anchor_fired = False

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get("type")

            # Attachment events (PostToolUse hook output) — scan for [context-anchor]
            if msg_type == "attachment":
                att = obj.get("attachment") or {}
                if isinstance(att, dict):
                    att_text = str(att.get("content") or "")
                    if "[context-anchor]" in att_text.lower():
                        identity_anchor_fired = True

            # Timestamps
            ts = obj.get("message", {}).get("timestamp") or obj.get("timestamp")
            if ts and isinstance(ts, str):
                try:
                    parsed_ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if first_timestamp is None:
                        first_timestamp = parsed_ts
                    last_timestamp = parsed_ts
                except (ValueError, TypeError):
                    pass

            # Assistant messages — greeting detection + tool calls
            if msg_type == "assistant":
                content_list = obj.get("message", {}).get("content", [])
                for block in content_list:
                    if not isinstance(block, dict):
                        continue

                    if block.get("type") == "text":
                        text_lower = block.get("text", "").lower()
                        if not greeted_as_mind:
                            head = text_lower[:200].lstrip()
                            m = GREETING_PREFIX.match(head)
                            if m:
                                mind_name = m.group(1).lower()
                                greeted_as_mind = True
                            else:
                                m = GREETING_INTRO.search(text_lower[:200])
                                if m:
                                    mind_name = m.group(1).lower()
                                    greeted_as_mind = True

                    if block.get("type") == "tool_use":
                        tool_name = block.get("name", "unknown")
                        tool_input = block.get("input", {}) or {}

                        is_memory_read = False
                        if tool_name == "Read":
                            fp = tool_input.get("file_path", "") or ""
                            if any(sig in fp for sig in (
                                "working-memory.md", "MEMORY.md", "memory/",
                                "CLAUDE.md", "PROJECT.md",
                            )):
                                is_memory_read = True

                        if is_memory_read:
                            category = "meta"
                        elif tool_name in EXPLORATION_TOOLS:
                            category = "exploration"
                        elif tool_name in PRODUCTIVE_TOOLS:
                            category = "productive"
                        elif tool_name in META_TOOLS:
                            category = "meta"
                        elif tool_name == "Bash":
                            cmd = tool_input.get("command", "") or ""
                            if any(kw in cmd for kw in ("git ", "ls ", "pytest", "npm test", "vitest")):
                                category = "exploration"
                            elif any(kw in cmd for kw in ("mkdir", "cp ", "mv ")):
                                category = "productive"
                            else:
                                category = "bash_other"
                        else:
                            category = "other"

                        tool_calls.append({"name": tool_name, "category": category})

            # User messages — emotional signals + memory load detection
            if msg_type == "user":
                content_raw = obj.get("message", {}).get("content", "")
                user_texts = []
                if isinstance(content_raw, str):
                    user_texts.append(content_raw)
                elif isinstance(content_raw, list):
                    for block in content_raw:
                        if isinstance(block, dict) and block.get("type") == "text":
                            user_texts.append(block.get("text", ""))

                for utext in user_texts:
                    tl = utext.lower()
                    if "[context-anchor]" in tl:
                        identity_anchor_fired = True
                    for sig in STRONG_NEGATIVE:
                        if sig in tl:
                            strong_neg = True
                            neg_count += 1
                    for sig in NEGATIVE_SIGNALS:
                        if sig in tl:
                            neg_count += 1
                    for sig in POSITIVE_SIGNALS:
                        if sig in tl:
                            pos_count += 1
                    for sig in ("wrong", "not what", "again", "told you", "keep doing"):
                        if sig in tl:
                            correction_topic_counts[sig] = correction_topic_counts.get(sig, 0) + 1
                            if correction_topic_counts[sig] >= 2:
                                repeated_corrections += 1

                # Memory-load detection in tool-result blocks
                if isinstance(content_raw, list):
                    for block in content_raw:
                        if not isinstance(block, dict):
                            continue
                        inner = block.get("content", "")
                        text = block.get("text", "")
                        candidates = []
                        if isinstance(text, str):
                            candidates.append(text)
                        if isinstance(inner, str):
                            candidates.append(inner)
                        elif isinstance(inner, list):
                            for ib in inner:
                                if isinstance(ib, dict):
                                    candidates.append(ib.get("text", "") or "")
                        for t in candidates:
                            if "working-memory.md" in t:
                                memory_loaded = True
                            if "[context-anchor]" in t.lower():
                                identity_anchor_fired = True
                            if "token-estimate:" in t and working_memory_tokens == 0:
                                try:
                                    part = t.split("token-estimate:")[1].split("-->")[0]
                                    nums = part.strip().replace("~", "").split("/")
                                    if nums:
                                        working_memory_tokens = int(nums[0])
                                except (IndexError, ValueError):
                                    pass
                elif isinstance(content_raw, str):
                    if "working-memory.md" in content_raw:
                        memory_loaded = True

    total = len(tool_calls)
    exploration = sum(1 for t in tool_calls if t["category"] == "exploration")
    productive = sum(1 for t in tool_calls if t["category"] == "productive")
    bash_other = sum(1 for t in tool_calls if t["category"] == "bash_other")
    meta = sum(1 for t in tool_calls if t["category"] == "meta")
    agents = sum(1 for t in tool_calls if t["name"] == "Agent")

    first_edit_idx = -1
    exploration_before_edit = total
    for i, t in enumerate(tool_calls):
        if t["category"] == "productive":
            first_edit_idx = i + 1
            exploration_before_edit = sum(
                1 for t2 in tool_calls[:i] if t2["category"] == "exploration"
            )
            break

    duration_min = 0
    if first_timestamp and last_timestamp:
        duration_min = round((last_timestamp - first_timestamp).total_seconds() / 60, 1)

    session_id = os.path.basename(jsonl_path).replace(".jsonl", "")[:8]

    return {
        "timestamp": (first_timestamp.strftime("%Y-%m-%d %H:%M")
                      if first_timestamp else datetime.now().strftime("%Y-%m-%d %H:%M")),
        "session_id": session_id,
        "project_dir": os.path.basename(os.path.dirname(jsonl_path)),
        "duration_minutes": duration_min,
        "total_tool_calls": total,
        "exploration_calls": exploration,
        "productive_calls": productive,
        "bash_calls": bash_other,
        "meta_calls": meta,
        "agent_calls": agents,
        "first_edit_index": first_edit_idx,
        "exploration_before_first_edit": exploration_before_edit,
        "working_memory_tokens": working_memory_tokens,
        "memory_loaded": memory_loaded,
        "negative_signals": neg_count,
        "positive_signals": pos_count,
        "strong_negative": strong_neg,
        "repeated_corrections": repeated_corrections,
        "mind_name": mind_name,
        "greeted_as_mind": greeted_as_mind,
        "identity_anchor_fired": identity_anchor_fired,
    }


def append_metrics(metrics):
    os.makedirs(METRICS_DIR, exist_ok=True)
    file_exists = os.path.exists(METRICS_FILE)
    with open(METRICS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(metrics)


def main():
    if len(sys.argv) > 1:
        jsonl_path = sys.argv[1]
    else:
        jsonl_path = find_latest_transcript()

    if not jsonl_path or not os.path.exists(jsonl_path):
        print("[minds-metrics] No transcript found", file=sys.stderr)
        sys.exit(0)  # Don't fail the SessionEnd hook

    try:
        metrics = parse_transcript(jsonl_path)
        append_metrics(metrics)
        print(f"[minds-metrics] Session {metrics['session_id']} logged "
              f"({metrics['total_tool_calls']} tool calls, "
              f"memory={'loaded' if metrics['memory_loaded'] else 'not loaded'})")
    except Exception as e:
        print(f"[minds-metrics] Error: {e}", file=sys.stderr)
        sys.exit(0)  # Never fail the hook


if __name__ == "__main__":
    main()
