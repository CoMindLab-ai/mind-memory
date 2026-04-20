# Memory Architecture

## Four tiers, by lifespan

Memory in Minds is organised by how long things should live, not by what topic they cover.

```
┌────────────────────────────────────────────────────────────────────────┐
│  TIER 1 — IDENTITY                                        read-only    │
│  Who the mind is. Role, personality, rules it never breaks.            │
│  Loaded at session start. Rarely changes.                              │
│  File: identity/anchor.md                                              │
├────────────────────────────────────────────────────────────────────────┤
│  TIER 2 — LONG-TERM MEMORY                                weeks+       │
│  Confirmed patterns, user profile, project lessons, heuristics.        │
│  Updated when patterns confirm 3+ times during consolidation.          │
│  File: memory/MEMORY.md (index) + memory/{topic}.md (details)          │
├────────────────────────────────────────────────────────────────────────┤
│  TIER 3 — WORKING MEMORY                                  days         │
│  Current focus, active blockers, recent corrections, last 5 sessions.  │
│  Updated every session. Entries >5 days old compress to Tier 4.        │
│  File: memory/working-memory.md                                        │
├────────────────────────────────────────────────────────────────────────┤
│  TIER 4 — ARCHIVE                                         rarely read  │
│  Compressed historical context. Not loaded by default.                 │
│  File: memory/archive.md                                               │
└────────────────────────────────────────────────────────────────────────┘
```

A useful mental model: **Tier 1 is personality. Tier 2 is what your colleague knows about the job. Tier 3 is what they remember from this week. Tier 4 is stuff they'd need to dig through notes to recall.**

## Loading strategy

At session start, Claude reads files in priority order:

1. `CLAUDE.md` — project conventions (always)
2. `identity/anchor.md` — who the mind is (if identity is configured)
3. `memory/MEMORY.md` — the long-term index (pointers to detailed files)
4. `memory/working-memory.md` — this week's state

The index pattern matters. `MEMORY.md` is short — one line per memory, pointing to the detailed file. Something like:

```markdown
## User Preferences
- [Audio Speed](feedback_audio_speed.md) — TTS at 1.25x speed
- [No Mocks](feedback_no_mocks.md) — integration tests hit real DB, prior incident

## Project Lessons
- [Auth Middleware](lesson_auth_middleware.md) — session tokens compliance rewrite
```

Claude loads the index at session start. When a relevant topic comes up, it reads the specific file. This keeps the always-loaded context small (~1-2KB) while making thousands of memories available on demand.

## The consolidation loop

Memory gets better through a recurring loop: **collect signals during the session, consolidate at the end**.

### Signals collected during session

- **Corrections** — user disagreement, pushback, "no", "don't", "wrong"
- **Confirmations** — user agreement, "yes exactly", "perfect, keep doing that"
- **Follow-through** — user accepts output without changes (silent confirmation)
- **Frustration markers** — strong negative language, "again?", "as I said"
- **Repeated topics** — same correction fires 2+ times across a session

These get detected by a hook that parses the session transcript. No ML, just pattern matching. Output: a structured summary of what was worth remembering.

### Consolidation at session end

A `/document` skill (or a session-end hook) runs the consolidation:

1. **Read working-memory.md** — what was already known
2. **Read session signals** — corrections, confirmations, repeated topics
3. **Propose updates**:
   - New correction not in memory → add as hunch
   - Existing hunch confirmed 3rd time → promote to heuristic
   - Contradicted heuristic → flag for review
   - Completed project → archive entries older than 5 days
4. **Write back** — update working-memory.md, MEMORY.md, archive.md

The user can run this manually (`/document`) or wire it to a Stop hook for automatic end-of-session consolidation.

## The "hunch → heuristic" promotion rule

Not every correction becomes a permanent rule. That would lead to memory pollution and contradictions.

Minds uses a 3-confirmation rule borrowed from scientific reasoning:

```
1st occurrence    → log as observation (not in memory yet)
2nd occurrence    → add as hunch (tentative, labelled)
3rd occurrence    → promote to heuristic (permanent, applied)
Contradicted      → demote to hunch, or archive with note
Consistent silence → stays in memory unchanged
```

This keeps the memory curated. A one-off correction in a weird edge case doesn't become a rule. A pattern that repeats across a month does.

## What actually gets stored

From real memory files in production use:

### User profile (Tier 2)
```markdown
---
name: Audio Speed preference
type: feedback
---
TTS audio at 1.25x speed (edge-tts rate "+10%").

Why: user prefers faster delivery for informational audio.
How to apply: any audio generation task, unless explicitly told otherwise.
```

### Project lesson (Tier 2)
```markdown
---
name: Auth middleware rewrite
type: project
---
Auth middleware rewrite is compliance-driven (legal flagged session
token storage), not tech-debt cleanup.

Why: EU regulatory deadline, not engineering preference.
How to apply: scope decisions should favour compliance correctness
over developer ergonomics.
```

### Heuristic (Tier 2)
```markdown
---
name: No mocks in integration tests
type: feedback
---
Integration tests must hit a real database, not mocks.

Why: prior incident where mocked tests passed but prod migration broke.
How to apply: set up copy-of-prod sqlite fixture per test, never
patch the DB layer.
```

Each file has frontmatter (name, type, description) and a body with the rule plus **why** and **how to apply**. The "why" is the most important field — it lets the mind judge edge cases instead of blindly following.

## What Minds is NOT

- **Not a vector database.** No embeddings, no similarity search. Plain markdown, loaded directly.
- **Not fine-tuning.** The model doesn't change. Only the context does.
- **Not a framework.** No SDK, no abstractions. Just files and two small Python hooks.
- **Not opaque.** You can read and edit every byte of what the system knows about you.
- **Not scale-infinite.** Optimised for thousands of memories, not millions. If you need millions, use a real DB.

## Why this beats a plain CLAUDE.md

A [CLAUDE.md](https://docs.claude.com/en/docs/claude-code/memory) file is great for *stable* project conventions. But it doesn't:

- Grow from usage — you have to manually edit it every time you want to add a lesson
- Distinguish hunches from confirmed rules — everything is equally weighted
- Archive stale content — it just keeps growing until it's too big to be useful
- Measure its own effectiveness — no feedback loop

Minds adds all four. It's CLAUDE.md with a growth model.

## Implementation footprint

The whole system, in files:

```
.claude/
  hooks/
    session-metrics.py      (~400 lines, measurement)
    metrics-brain.py        (~250 lines, weekly analysis)
  settings.json             (~50 lines, hook wiring)
memory/
  MEMORY.md                 (index, grows with content)
  working-memory.md         (~5KB budget, rolls over)
  archive.md                (compressed history)
  {topic}.md                (one per memory, N files)
skills/
  mind-setup.md             (the wizard, ~200 lines)
CLAUDE.md                   (project conventions, unchanged)
```

Total added weight: ~2MB of markdown for a year of active use. Negligible next to `node_modules`.

## Next

The architecture above is the mechanism. The next question is: **does it actually help?** That's what [03-findings.md](03-findings.md) answers — with data from 3 months of daily use and full honesty about what we don't yet know.

---

*CoMindLab Labs — Minds research, 2026.*
