"""Metrics Brain — weekly analyser for the MindMemory memory system.

Reads .claude/metrics/session-metrics.csv, computes the five hypotheses
(H1–H5), compares this week to last week, and writes a markdown report
to .claude/metrics/daily-report.md.

Can be run standalone or from a scheduled task. Idempotent — skips if
already run today.

Hypotheses:
  H1 Production ratio      — productive_calls / total_calls  (higher = better)
  H2 Orientation speed     — exploration calls before first edit  (lower = better)
  H3 Agent efficiency      — agent_calls / total_calls  (lower = better)
  H4 Session density       — productive calls per session  (higher = better)
  H5 Repeat-correction     — % sessions with repeat_corrections > 0  (lower = better)

Also runs a matched-cohort comparison: sessions with memory loaded vs
not, filtered to comparable session sizes (>=30 tool calls).

Generic — no assumptions about mind names. MIT — CoMindLab Labs.
"""
import csv
import os
import sys
from collections import defaultdict
from datetime import datetime


METRICS_FILE = os.path.join(os.getcwd(), ".claude", "metrics", "session-metrics.csv")
REPORT_FILE = os.path.join(os.getcwd(), ".claude", "metrics", "daily-report.md")
LAST_RUN = os.path.join(os.getcwd(), ".claude", "metrics", ".brain-last-run")

MIN_SESSIONS_FOR_VERDICT = 30
MATCHED_COHORT_MIN_TOOLS = 30


def already_ran_today():
    if not os.path.exists(LAST_RUN):
        return False
    try:
        with open(LAST_RUN, "r") as f:
            return f.read().strip() == datetime.now().strftime("%Y-%m-%d")
    except (IOError, ValueError):
        return False


def mark_ran():
    os.makedirs(os.path.dirname(LAST_RUN), exist_ok=True)
    with open(LAST_RUN, "w") as f:
        f.write(datetime.now().strftime("%Y-%m-%d"))


def _int(v, default=0):
    try:
        return int(v) if v not in ("", None) else default
    except (ValueError, TypeError):
        return default


def _bool(v):
    return v == "True"


def load_sessions():
    if not os.path.exists(METRICS_FILE):
        return []
    sessions = []
    with open(METRICS_FILE, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                row["total_tool_calls"] = _int(row.get("total_tool_calls"))
                row["productive_calls"] = _int(row.get("productive_calls"))
                row["exploration_calls"] = _int(row.get("exploration_calls"))
                row["agent_calls"] = _int(row.get("agent_calls"))
                row["first_edit_index"] = _int(row.get("first_edit_index"), -1)
                row["exploration_before_first_edit"] = _int(row.get("exploration_before_first_edit"))
                row["memory_loaded"] = _bool(row.get("memory_loaded"))
                row["negative_signals"] = _int(row.get("negative_signals"))
                row["positive_signals"] = _int(row.get("positive_signals"))
                row["repeated_corrections"] = _int(row.get("repeated_corrections"))
                sessions.append(row)
            except (ValueError, KeyError):
                continue
    return sessions


def compute_weekly_metrics(sessions):
    weeks = defaultdict(list)
    for s in sessions:
        try:
            dt = datetime.strptime(s.get("timestamp", "")[:10], "%Y-%m-%d")
            weeks[dt.strftime("%Y-W%W")].append(s)
        except (ValueError, IndexError):
            continue

    out = {}
    for week, ss in sorted(weeks.items()):
        real = [s for s in ss if s["total_tool_calls"] > 5]
        if not real:
            continue

        total = sum(s["total_tool_calls"] for s in real)
        prod = sum(s["productive_calls"] for s in real)
        agents = sum(s["agent_calls"] for s in real)
        edits = [s for s in real if s["first_edit_index"] > 0]

        repeat_sessions = sum(1 for s in real if s["repeated_corrections"] > 0)

        out[week] = {
            "sessions": len(real),
            "h1_production_ratio": round(prod / total * 100, 1) if total else 0,
            "h2_orientation_speed": round(
                sum(s["exploration_before_first_edit"] for s in edits) / len(edits), 1
            ) if edits else 0,
            "h3_agent_ratio": round(agents / total * 100, 1) if total else 0,
            "h4_session_density": round(prod / len(real), 1),
            "h5_repeat_rate": round(repeat_sessions / len(real) * 100, 1),
            "memory_loaded": sum(1 for s in real if s["memory_loaded"]),
        }
    return out


def compute_matched_cohort(sessions):
    comparable = [s for s in sessions if s["total_tool_calls"] >= MATCHED_COHORT_MIN_TOOLS]
    groups = {"loaded": [], "not_loaded": []}
    for s in comparable:
        (groups["loaded"] if s["memory_loaded"] else groups["not_loaded"]).append(s)

    out = {}
    for label, group in groups.items():
        if not group:
            out[label] = None
            continue
        n = len(group)
        total = sum(s["total_tool_calls"] for s in group)
        prod = sum(s["productive_calls"] for s in group)
        agents = sum(s["agent_calls"] for s in group)
        edits = [s for s in group if s["first_edit_index"] > 0]
        repeat = sum(1 for s in group if s["repeated_corrections"] > 0)
        neg = sum(1 for s in group if s["negative_signals"] > 0)
        out[label] = {
            "n": n,
            "h1": round(prod / total * 100, 1) if total else 0,
            "h2": round(
                sum(s["exploration_before_first_edit"] for s in edits) / len(edits), 1
            ) if edits else 0,
            "h3": round(agents / total * 100, 1) if total else 0,
            "h4": round(prod / n, 1),
            "h5": round(repeat / n * 100, 1),
            "neg_rate": round(neg / n * 100, 1),
        }
    return out


def trend_arrow(current, previous):
    if previous == 0:
        return "--"
    diff = ((current - previous) / previous) * 100
    if abs(diff) < 3:
        return f"= ({diff:+.0f}%)"
    return f"^ ({diff:+.0f}%)" if diff > 0 else f"v ({diff:+.0f}%)"


def write_report(weekly, matched):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    weeks = sorted(weekly.keys())
    lines = [f"# MindMemory Metrics Report — {now}", ""]

    if len(weeks) < 2:
        lines.append(f"Not enough weekly data. {len(weeks)} week(s) available.")
        lines.append("Keep using for at least 2 weeks for a real comparison.")
    else:
        current = weekly[weeks[-1]]
        previous = weekly[weeks[-2]]

        lines.append(f"## Weekly comparison: {weeks[-1]} vs {weeks[-2]}")
        lines.append(f"**Sessions:** {current['sessions']} (this week) vs {previous['sessions']} (last week)")
        lines.append(f"**Memory loaded:** {current['memory_loaded']}/{current['sessions']} sessions")
        lines.append("")

        if current["sessions"] < MIN_SESSIONS_FOR_VERDICT or previous["sessions"] < MIN_SESSIONS_FOR_VERDICT:
            lines.append(
                f"VERDICT SUPPRESSED: need >={MIN_SESSIONS_FOR_VERDICT} sessions per week for a stable signal. "
                f"(this={current['sessions']}, last={previous['sessions']})"
            )
        else:
            lines.append("| Hypothesis | Metric | Last week | This week | Trend |")
            lines.append("|-----------|--------|-----------|-----------|-------|")
            lines.append(
                f"| H1 Production ratio | productive/total | {previous['h1_production_ratio']}% | {current['h1_production_ratio']}% | {trend_arrow(current['h1_production_ratio'], previous['h1_production_ratio'])} |"
            )
            lines.append(
                f"| H2 Orientation speed | calls before edit | {previous['h2_orientation_speed']} | {current['h2_orientation_speed']} | {trend_arrow(previous['h2_orientation_speed'], current['h2_orientation_speed'])} |"
            )
            lines.append(
                f"| H3 Agent efficiency | agent/total | {previous['h3_agent_ratio']}% | {current['h3_agent_ratio']}% | {trend_arrow(previous['h3_agent_ratio'], current['h3_agent_ratio'])} |"
            )
            lines.append(
                f"| H4 Session density | productive/session | {previous['h4_session_density']} | {current['h4_session_density']} | {trend_arrow(current['h4_session_density'], previous['h4_session_density'])} |"
            )
            lines.append(
                f"| H5 Repeat-correction rate | % sessions w/ repeats | {previous['h5_repeat_rate']}% | {current['h5_repeat_rate']}% | {trend_arrow(previous['h5_repeat_rate'], current['h5_repeat_rate'])} |"
            )
            lines.append("")

            improving = 0
            if current["h1_production_ratio"] > previous["h1_production_ratio"]:
                improving += 1
            if current["h2_orientation_speed"] < previous["h2_orientation_speed"]:
                improving += 1
            if current["h3_agent_ratio"] < previous["h3_agent_ratio"]:
                improving += 1
            if current["h4_session_density"] > previous["h4_session_density"]:
                improving += 1
            if current["h5_repeat_rate"] < previous["h5_repeat_rate"]:
                improving += 1

            lines.append(f"**Score: {improving}/5 hypotheses trending in expected direction.**")
            if improving >= 4:
                lines.append("Memory system appears to be helping.")
            elif improving >= 3:
                lines.append("Positive lean — keep watching.")
            elif improving >= 2:
                lines.append("Mixed signals — need more data.")
            else:
                lines.append("No measurable impact yet.")

    lines.append("")
    lines.append(f"## Matched cohort: mem-loaded vs not (sessions >={MATCHED_COHORT_MIN_TOOLS} tools)")
    loaded = matched.get("loaded")
    not_loaded = matched.get("not_loaded")
    if not loaded or not not_loaded:
        lines.append("Not enough data in one of the groups. Keep using.")
    else:
        lines.append("| Group | n | H1 Prod% | H2 Orient | H3 Agent% | H4 Density | H5 Repeat% | Neg% |")
        lines.append("|-------|---|----------|-----------|-----------|------------|------------|------|")
        lines.append(
            f"| LOADED     | {loaded['n']} | {loaded['h1']}% | {loaded['h2']} | {loaded['h3']}% | {loaded['h4']} | {loaded['h5']}% | {loaded['neg_rate']}% |"
        )
        lines.append(
            f"| NOT loaded | {not_loaded['n']} | {not_loaded['h1']}% | {not_loaded['h2']} | {not_loaded['h3']}% | {not_loaded['h4']} | {not_loaded['h5']}% | {not_loaded['neg_rate']}% |"
        )

    lines.append("")
    lines.append("## Weekly history (last 10 weeks)")
    lines.append("| Week | N | H1 Prod% | H2 Orient | H3 Agent% | H4 Density | H5 Repeat% | MemLoad |")
    lines.append("|------|---|----------|-----------|-----------|------------|------------|---------|")
    for w in weeks[-10:]:
        m = weekly[w]
        lines.append(
            f"| {w} | {m['sessions']} | {m['h1_production_ratio']}% | {m['h2_orientation_speed']} | "
            f"{m['h3_agent_ratio']}% | {m['h4_session_density']} | {m['h5_repeat_rate']}% | "
            f"{m['memory_loaded']}/{m['sessions']} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("*Generated by MindMemory metrics-brain. Read `starter-kit/README.md` for what these numbers mean.*")

    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[minds-brain] Report written to {REPORT_FILE}")


def main():
    if already_ran_today() and "--force" not in sys.argv:
        sys.exit(0)
    sessions = load_sessions()
    if not sessions:
        print("[minds-brain] No session data yet. Use Claude Code for a while.")
        sys.exit(0)
    weekly = compute_weekly_metrics(sessions)
    matched = compute_matched_cohort([s for s in sessions if s["total_tool_calls"] > 5])
    write_report(weekly, matched)
    mark_ran()


if __name__ == "__main__":
    main()
