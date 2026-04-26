# Open Questions

*What we don't know. Where we want critique.*

We're publishing this as a research artefact, not a finished product. These are the questions we're genuinely unsure about. If you have strong opinions, we want to hear them — see [contact](#how-to-engage) at the bottom.

## On the architecture

### 1. Is the 3-confirmation promotion rule right?

We promote a "hunch" to a "heuristic" after 3 occurrences. The number is arbitrary. 2 might be enough (faster learning, more noise). 5 might be safer (slower, more robust). Nobody's tested alternatives.

**What would help**: users running with different thresholds (2, 3, 5) and reporting subjective feel + H5 rate.

### 2. Is markdown the right representation?

We chose markdown because it's:
- Native to Claude (no retrieval step)
- Human-readable and -editable
- Narrative, not tabular (closer to how memory actually works)

But markdown doesn't scale to millions of entries. And it's unindexed — Claude has to load everything it wants to consider.

**Open question**: at what scale does this break? When should the design switch to hybrid markdown + vector recall? 10k entries? 100k?

### 3. Is the 4-tier model the right decomposition?

Identity / Long-term / Working / Archive. Four tiers, organised by lifespan.

Alternative decompositions we considered:
- By **topic** (preferences / project / references / people) — clearer categories, harder to manage lifespan
- By **confidence** (hunch / heuristic / rule) — closer to the learning loop, doesn't address lifespan
- By **source** (user-stated / inferred / corrected) — provenance-aware, more complex

We picked lifespan because it maps cleanly onto "what do I load at session start". But we're not certain it's the best decomposition.

## On the measurement

### 4. Is H5 (repeat-correction rate) the right primary outcome?

H5 measures "% of sessions where the same correction fires 2+ times". Our thinking: memory should prevent that by surfacing the correction before it's needed again.

Problems with H5:
- Requires corrections to use specific language patterns to be detected
- A correction that happens in the first session (before memory exists) doesn't count against memory
- Doesn't capture the frustration the user described qualitatively

Alternatives considered:
- **Time-to-first-correction-in-a-session** — how long into a session before the user pushes back?
- **Novel-correction rate** — how often is the user saying something the system "should have known"?
- **User-reported frustration** (survey) — the gold standard, but expensive

**Open question**: what's the best measurable proxy for "this AI remembers me"?

### 5. How do we separate memory effect from selection effect?

Sessions that load memory are, empirically, bigger and harder. So any positive correlation could be "hard sessions are productive" rather than "memory makes sessions productive".

The clean experiment: randomly suppress memory loading for half of sessions for a week. We haven't run it. It would be disruptive for the primary user. But it's the only way to get a clean causal answer.

**Open question**: is there a smart quasi-experimental design that gives a causal answer without suppressing memory?

### 6. Is the instrumentation honest?

Our hooks detect:
- Negative language (30 patterns, including profanity and "you keep doing X")
- Positive language (14 patterns)
- Repeated corrections (5 correction keywords, flagged when same keyword fires 2+ times)

These are proxies. A polite user who types "hmm, not quite" won't register as negative. A user who repeats a correction with different wording each time won't trip the repeat detector.

**Open question**: what would a better proxy look like that doesn't require user-facing surveys?

## On the learning loop

### 7. Is session-end the right time to consolidate?

The session-end hook is convenient but has a flaw: by the time the session ends, the model that's doing the consolidation has already drifted. Mid-session consolidation (every 25 messages, as the larger CognitiveMemory system does) catches insights while they're fresh.

**Open question**: for the simple starter-kit case, is session-end good enough? Or should even the minimal version run mid-session consolidation?

### 8. Who should do the consolidation — the mind or a separate agent?

Two approaches:
- **Self-consolidation**: the mind that just worked reviews its own transcript and updates its memory. Risk: same reasoning blindspots that produced the mistakes also produced the self-review.
- **Critic consolidation**: a separate, fresh-context agent reviews the transcript. Less biased, but doesn't have the first-person perspective.

We currently use self-consolidation. Haven't tested critic.

**Open question**: is the selfbias enough of a problem to justify a second agent's cost?

## On the adoption model

### 9. Is the 5-minute install achievable in practice?

We've optimised for "copy 3 files, run `/cognitive-memory-setup`, done". That's fast on a fresh project. On an existing Claude Code project with a customised `.claude/settings.json`, it's harder — merging hook config is a manual step.

**Open question**: is there a cleaner integration pattern we're missing? A Claude Code plugin rather than a copy-paste?

### 10. Does measurement scare people off?

Our pitch includes "ships with hooks that measure whether it's helping you". That's important for research honesty but might sound like surveillance to privacy-conscious users.

The data stays local. Only the user sees it. We say this clearly. Is that enough?

**Open question**: how do we communicate "you can measure this yourself" without triggering "this is spying on me"?

### 11. What's the right default for sharing?

The starter kit includes a script to anonymise session metrics and send them to a shared dashboard (not yet built). Opt-in. Off by default. Are we right to make that opt-in, or would opt-out with very clear messaging produce better research data without genuine privacy cost?

Current stance: **opt-in, always**. We won't change that without strong community consensus.

## How to engage

If you have takes on any of these:

1. **GitHub issue** on the public repo (when published)
2. **Email** to `hello@comindlab.ai` — we read everything
3. **Tweet at us** (@comindlab) — shorter, more public

We particularly want engagement from:
- Researchers working on LLM memory (mem0, letta, MemGPT authors)
- Claude Code power users with lots of sessions
- Anyone who installs the starter kit and finds a failure mode we haven't documented

Critique is more useful than agreement. If you think we're wrong, tell us why.

---

*CoMindLab Labs — CognitiveMemory research, 2026.*
