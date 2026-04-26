# The Concept — From Agents to Minds

## The gap nobody's naming

AI coding tools have made a lot of progress in the last two years. Better models. Faster inference. More tools. Proper CLIs. Agent loops that actually loop.

But there's a gap that nobody's naming clearly: **AI tools don't remember you.**

Every conversation starts cold. Every project has to re-teach the same rules. Every preference you voiced yesterday is gone tomorrow. The tool gets smarter in aggregate, across the training run. It doesn't get smarter for *you*.

This isn't a prompt-engineering problem. It's a **context-engineering** problem. And it's the single biggest lever left for making AI coding tools feel less like a search box and more like a colleague.

## Where we are now

```
                 Agents                       OpenClaude                    Human mind
                 (stateless)                  (capable, forgetful)          (remembers, adapts)
                 ─────────                    ──────────────────            ──────────────
Capability       High (per call)              High (per call)               Variable
Memory           None                         Session only                  Lifelong, selective
Personality      None                         Prompted, thin                Deep, stable
Learning         Retrain the model            Retrain the model             Continuous
Trust            Transactional                Transactional                 Relational
```

The industry has focused on the left columns. Better tools, better agents, better single-call performance. Memory has been an afterthought — a vector DB bolted on, or a buffer that expires.

**CognitiveMemory** sits between OpenClaude and a human mind. It's the next evolution: **AI that remembers like a colleague**.

## What a "mind" actually is

A mind, in our usage, is the combination of three things Claude Code already supports — wired together in a specific way:

1. **Identity** — who the mind is. Role, personality, stable preferences, rules it never breaks. Lives in `identity/` files loaded at session start.

2. **Memory** — what the mind knows about you and the work. Layered by lifespan:
   - *Working memory* (this week) — current focus, recent corrections, active blockers
   - *Long-term memory* (months) — confirmed patterns, user profile, project lessons
   - *Archive* (rarely read) — everything older, compressed

3. **Heuristics** — rules of thumb learned from experience. When you correct the mind ("no, always run tests before claiming done"), that correction gets promoted to a heuristic after it's confirmed a few times. Heuristics are the thing that makes the mind *feel* different from session to session.

A mind is **one markdown-based construct** wrapping all three. You can make a "dev craftsperson" mind, a "research assistant" mind, a "content editor" mind. Each has its own identity, its own memory, its own heuristics. They can share infrastructure but think differently.

## The learning loop (Karpathy's insight)

Andrej Karpathy's [LLM Wiki framing](https://x.com/karpathy/status/2039805659525644595) ([also in this gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)) is the kernel here. The idea: an agent that writes down what worked and what didn't, in structured natural language, then reads those notes back at the start of the next session. Not fine-tuning. Not vector search on every token. Just a curated, ever-improving wiki that the agent itself maintains.

CognitiveMemory implements that loop with **three concentric maintenance cycles**, not just session bookends. Self-maintenance is continuous — the system curates itself while you work, not only when you log off.

```
┌─────────────────────────────────────────────────────────────────────┐
│ INNER LOOP — every N tool calls (mid-session, PostToolUse hook)     │
│   memory-collector  → scans live transcript, captures fresh         │
│                       corrections / confirmations / follow-through  │
│   memory-curator    → promotes hunch → heuristic after 3 fires;     │
│                       demotes contradicted rules; archives stale    │
└─────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ fires repeatedly
                              │ during the session
┌─────────────────────────────────────────────────────────────────────┐
│ MIDDLE LOOP — per session                                            │
│   SessionStart  → load identity + MEMORY.md + working-memory         │
│                   + health check (warns if curator hasn't run >7d)   │
│   SessionEnd    → session-metrics writes one row to CSV              │
└─────────────────────────────────────────────────────────────────────┘
                              ▲
                              │ wraps each session
┌─────────────────────────────────────────────────────────────────────┐
│ OUTER LOOP — weekly, time-gated                                      │
│   metrics-brain     → reads CSV, computes H1–H5, writes report       │
│   memory-index      → regenerates INDEX.md (optional feature)        │
└─────────────────────────────────────────────────────────────────────┘
```

Three signals drive the inner loop:

- **Corrections** ("no", "wrong", "don't do that again") → candidate new heuristics
- **Confirmations** ("yes exactly", "keep doing that") → reinforcement of existing approach
- **Follow-through** (user accepts output without pushback) → silent confirmation

A pattern that fires 3+ times gets promoted from "hunch" to "rule". A rule that's contradicted gets demoted or rewritten. **The wiki maintains itself, mid-session, without waiting for end-of-session.**

Why mid-session matters: by the time a session ends, the model that would do the consolidation has already drifted from the moment of insight. Catching corrections within minutes of them happening produces tighter, more specific rules than catching them hours later. Session-end consolidation is the safety net, not the primary mechanism.

## Why markdown, not a database

Deliberate choice. Three reasons:

1. **Closer to human mind structure than a DB.** Memory isn't rows. It's narrative, threaded, lossy, prioritised. Markdown reflects that better than tables.

2. **Claude reads markdown natively.** Every byte of context is a direct input. No query language, no embedding lookup, no retrieval accuracy to tune. If it's in the file, the model sees it.

3. **Humans can read and edit it.** The biggest failure mode of LLM memory systems is opacity — you can't tell what the system thinks it knows. With markdown files, you open them, read them, fix them. Full transparency, full control.

The tradeoff: markdown doesn't scale to millions of entries. That's fine. Human working memory doesn't either. The whole system is calibrated around "what a colleague would plausibly remember" — thousands of entries, not millions.

## What we're publishing

This research folder is the **generic, portable kernel** of the CognitiveMemory idea. Not a framework. Not a SaaS. A small set of files you can drop into any Claude Code project plus a setup wizard that personalises them to you.

If the kernel works — if people adopt it, extend it, disagree with us — the bigger system (multiple minds, daemons, auto-consolidation) can follow. Start small, prove the idea, let the community take it further than we can.

## The three principles we're testing publicly

1. **Structured memory beats prompt engineering.** Put effort into the files, not the prompts.
2. **Continuous self-maintenance beats end-of-session batch.** Catch corrections mid-session while they're fresh, not hours later when context has drifted. Session-end is the safety net, not the primary loop.
3. **Measurement keeps you honest.** Ship metrics with the memory system. If you can't measure whether memory is helping, you're guessing.

The next two documents ([02-memory-architecture.md](02-memory-architecture.md) and [03-findings.md](03-findings.md)) unpack how we built this and what the data says after 3 months of daily use.

The honest answer to "is it working?" is *partially, and we have the numbers to show you exactly where*. More in findings.

---

*CoMindLab Labs — CognitiveMemory research, 2026.*
