# Architecture

Design decisions and the reasoning behind them.

## Goal

Make structured memory navigable. As `memory/rules/` and `memory/working-memory.md` accumulate entries, the answer to "is there a rule for this?" should take five seconds, not five minutes.

## Non-goals

- Replacing search. `grep` across `memory/` is fast and correct. INDEX.md is for browsing, not findability.
- Bidirectional links. We considered `[[wiki-link]]` syntax in source files and rejected it — link rot at scale (rename a file, twenty backlinks break silently) and cognitive tax on every documentation moment.
- LLM-driven clustering or semantic grouping. Adds opacity, network dependency, and cost for marginal value at small N.

## What is indexed

| Source | Convention | Why |
|--------|-----------|-----|
| `memory/rules/*.md` | One rule per file. Title = first `# Heading`, fallback to filename. | Rules are stable, file-per-rule already enforced. |
| `memory/working-memory.md` | Bullets under `### Key Decisions`. Date format `(YYYY-MM-DD)`. | Working memory is the natural home of evolving decisions. The dedicated section keeps churn separate from indexable content. |

Heuristics, hunches, project notes, sessions are **not** indexed. They're operational reflex tables and ephemeral state — mixing them dilutes signal.

## Why flat lists at small N

The first prototype clustered entries by token-overlap. With 17 entries from a tight engineering domain, every rule shared two-plus meaningful tokens with every other rule, producing one mega-cluster labelled `"never, file, apply"`. Useless. Worse: it looked organised when it wasn't, which is dishonest output.

Flat sorted lists at <50 entries:

- Trivially correct
- Faster to scan than fake clusters
- Surface the dates on decisions (newest first), which is the actual primary key for "what was the latest call on X?"

When the corpus passes ~50 entries we re-introduce clustering — but with a centroid-based algorithm, source-segregated, and only after measuring whether flat-list-with-grep already solved it.

## Why SessionStart, not cron or daemon

| Option | Verdict |
|--------|---------|
| Daemon scheduled job | Requires the user to run a daemon. Out of scope for a drop-in folder. |
| Cron / Task Scheduler | Per-OS configuration, brittle, invisible to the user. |
| SessionStart hook with 7-day gate | Native to Claude Code. Self-throttling. Visible in `settings.json`. Survives reboots. |

The hook gate costs ~1ms when blocking. When it fires, it spawns the generator as a fire-and-forget background process — session start is never blocked.

## Why no LLM, no network, no third-party deps

Three reasons:

1. **Reproducibility.** Same input, same output, every time.
2. **Audit.** A user reading `memory_index_generate.py` can see exactly what's classified and why.
3. **Cost.** This runs weekly, forever, on every project that adopts it.

Pure Python stdlib. Total dependencies: zero.

## Failure modes the design accepts

- **Unparseable working-memory.md.** If the `### Key Decisions` heading is missing, decisions count is zero. The script logs and continues — does not crash.
- **No sources.** Returns exit code 1 with a message; the hook ignores it (errors swallowed by design).
- **Custom date formats in decisions.** Only `(YYYY-MM-DD)` is parsed. Anything else, the entry is still indexed but sorts to the bottom.
- **Unicode / encoding.** Files are read with `errors="replace"` so a single bad byte does not abort the run.

## File layout invariants

Generator and hook locate the repo by walking up from their own file path. Moving them within the project breaks discovery. Everything else (memory dir, rules dir, output path) is config-driven.

## What changes when the corpus grows

Trigger to revisit:

- 50+ entries → reintroduce centroid-based clustering
- Multiple repos / monorepo → consider per-area sub-indexes
- Users hand-editing INDEX.md → that's the kill signal; the system is failing them

## Kill clause

If `memory/INDEX.md` is not opened within four weeks of install, the feature has not earned its slot. Delete it.
