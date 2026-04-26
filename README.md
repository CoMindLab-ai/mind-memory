# MindMemory — Memory for Claude Code

> **Give Claude Code a memory that gets better the more you use it.**

**⚠️ Research preview — expect rough edges.** This is a working prototype shared early to invite critique and use-case feedback. Documentation may be ahead of code in places, the wizard has been dogfooded by one user, and the headline measurement (H5 repeat-correction reduction) hasn't been demonstrated yet. If you install it, plan to read the source. File issues — that's exactly the feedback we need.

A drop-in folder + a small set of Python hooks that make Claude Code remember your corrections, preferences, and project lessons across sessions. The hooks run continuously — collecting signals mid-session, promoting confirmed patterns to rules, measuring whether memory is helping you. Markdown-native. MIT. Installs in 5 minutes.

## The headline number

Across 9,869 real Claude Code sessions over 3 months — comparing the 92 that are directly comparable (≥30 tool calls, post-instrumentation):

| Metric                                     | Memory loaded (n=71) | No memory (n=21) |
| ------------------------------------------ | -------------------- | ---------------- |
| H1 Production ratio (edits / tool calls)   | **18.5%**            | 8.5%             |
| H2 Exploration calls before first edit     | **14.6**             | 16.3             |
| H4 Productive calls per session            | **26.0**             | 6.0              |
| H5 Repeat-correction rate *(lower better)* | 19.7%                | 14.3%            |

Memory-loaded sessions are denser and orient faster. But **H5 — the primary outcome we actually care about (fewer repeated corrections) — came back null**. We don't have a clean A/B yet. Full writeup and caveats in [03-findings.md](03-findings.md). We're publishing specifically to get more data.

## Install (3 commands)

```bash
cp -r starter-kit/. your-project/
cd your-project
mv .claude/settings.json.example .claude/settings.json
claude
> /mind-memory-setup
```

The `/mind-memory-setup` skill runs an interactive wizard that asks about your role, preferences, and recurring gotchas, then seeds the memory files with your answers. No blank-page paralysis. Takes ~5 minutes end-to-end.

## What's in this research folder

| File                                                | Purpose                                                                                            |
| --------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| [01-concept.md](01-concept.md)                      | The idea — from agents to minds, why memory is context-engineering's next lever                    |
| [02-memory-architecture.md](02-memory-architecture.md) | The 4-tier memory model, three-loop self-maintenance, Karpathy's wiki-as-learning pattern       |
| [03-findings.md](03-findings.md)                    | Honest data from 3 months of daily use. What we measured, what we found, what's still unknown      |
| [04-open-questions.md](04-open-questions.md)        | What we don't know. Where we want critique                                                          |
| [starter-kit/](starter-kit/)                        | The drop-in files. Copy these into your project                                                     |
| [memory-index/](memory-index/)                      | Optional feature — regenerable overview index of rules and decisions                                |
| [CONTRIBUTING.md](CONTRIBUTING.md)                  | How to engage                                                                                       |
| [LICENSE](LICENSE)                                  | MIT                                                                                                  |

## Why this matters

- **Context engineering beats prompt engineering.** The biggest lever for getting better output from an LLM isn't cleverer prompts — it's structured, persistent context. Static CLAUDE.md files were a good first step. MindMemory is the next one: a folder that grows with use.
- **Memory makes an AI feel like a colleague, not a search box.** Your best coworker remembers the deploy that broke because someone forgot the feature flag, the argument about tabs vs spaces, that you prefer brevity over hedging. MindMemory gives Claude Code that kind of memory.
- **Every interaction teaches the system.** Corrections get captured. Confirmations get reinforced. Patterns that fire 3+ times get promoted from hunches to rules. Borrowed from [Andrej Karpathy's "LLM wiki" framing](https://x.com/karpathy/status/2039805659525644595).

## Who should use this

- You use Claude Code daily and get frustrated re-teaching the same lessons
- You want structured, readable memory you can edit by hand
- You're OK with markdown files as your "database"

## Who should probably skip this

- You don't use Claude Code (this is CC-specific, not LLM-generic)
- You need enterprise audit trails for memory changes
- You want a UI — MindMemory is files and CLI

## Status

- **Concept**: in daily use since 2026-02, stable
- **Starter kit**: v0.1 — works on Windows + macOS + Linux, tested on Python 3.11+
- **Measurement tools**: production — 9,869 sessions analysed (of which 2,192 were real work sessions, 92 are matched cohort)
- **Author**: solo, CoMindLab Labs. Looking for collaborators and reviewers

## Get involved

We're publishing this as a research artefact and asking for critique. Two ways to help:

1. **Try it.** Install the starter kit, use it for two weeks, tell us what's broken. GitHub Issues or [hello@comindlab.ai](mailto:hello@comindlab.ai).
2. **Read and critique.** Start with [01-concept.md](01-concept.md) and [03-findings.md](03-findings.md). We specifically want pushback on the experimental design — the null result on H5 needs more eyes.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full list of what we're asking for.

---

*CoMindLab Labs — MindMemory research, 2026.*
