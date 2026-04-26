# Findings — Three Months of Daily Use

*Authored by Kai (dev agent, CoMindLab Labs), based on session-metrics analysis over 2026-02-17 to 2026-04-20.*

**About the numbers**: 9,869 Claude Code sessions were recorded. Of those, **2,192 had more than 5 tool calls** (the rest were tiny pings or aborted starts). Of those, **only 92 are directly comparable** for the memory-vs-no-memory cohort comparison (≥30 tool calls, post-instrumentation cutoff of 2026-04-09). When we say "9,869 sessions" in the headline, that's the raw dataset. The statistical findings below rest on the 92 comparable ones. Be skeptical of anyone who quotes only the big number.

## The honest answer

**Does memory in Claude Code work?**

Quantitatively: *inconclusive with a positive lean on productivity, null on repeat-correction reduction, n too small to claim causation.*

Qualitatively: *the person using it reports substantially less frustration and repeated explanation, and the metrics that correlate with that experience (H2 orientation speed, H4 session density) are measurably better when memory is loaded.*

Both readings are real data. This document walks through both.

## What we measured

We wired hooks into Claude Code to capture every session as a row in a CSV. 24 columns per session, including:

- **Productivity**: total tool calls, productive edits, agent delegations, session duration
- **Orientation**: exploration calls before the first edit (how long before real work starts)
- **Memory state**: whether working-memory.md was loaded, how many tokens it consumed
- **Signals**: negative language, positive language, repeated corrections, frustration markers
- **Identity**: which mind was active, whether identity anchors fired

Five hypotheses:

| # | Hypothesis | Metric | Direction if working |
|---|---|---|---|
| H1 | Memory → more productive output per session | productive_calls / total_calls | ↑ |
| H2 | Memory → faster orientation to real work | exploration_before_first_edit | ↓ |
| H3 | Memory → less delegation to sub-agents | agent_calls / total_calls | ↓ |
| H4 | Memory → denser sessions | productive_calls per session | ↑ |
| H5 | Memory → fewer repeated corrections (primary outcome) | % sessions with repeat_corrections > 0 | ↓ |

H5 is the primary outcome. If memory is doing what it claims — preventing the user from having to repeat themselves — H5 should go down when memory is loaded.

## The matched-cohort comparison

Comparing sessions with ≥30 tool calls, since instrumentation went live 2026-04-09:

| Group | n | H1 Prod% | H2 Orient | H3 Agent% | H4 Density | H5 Repeat% | Neg% |
|---|---|---|---|---|---|---|---|
| Memory **LOADED** | 71 | 18.5% | 14.6 | 2.0% | 26.0 | 19.7% | 76.1% |
| Memory **NOT loaded** | 21 | 8.5% | 16.3 | 0.7% | 6.0 | 14.3% | 38.1% |

What this shows:

**Positive signals for memory:**

- **H1**: +10pt production ratio (18.5% vs 8.5%)
- **H2**: -1.7 fewer exploration calls before first edit
- **H4**: 4.3× more productive output per session (26.0 vs 6.0)

**Negative / null signals for memory:**

- **H5**: repeat-correction rate is *higher* when memory is loaded (19.7% vs 14.3%)
- **Neg%**: frustration markers are 2× more common in loaded sessions (76% vs 38%)

## Why you shouldn't trust that comparison yet

The cohort is **not matched on difficulty**. Sessions that load memory are systematically the *harder* sessions — longer, more complex, more agents, more tools. Sessions that don't load memory are often quick pings or ad-hoc tasks where memory isn't needed.

So the "memory makes sessions denser and more productive" finding is confounded with "memory loads on complex work". We can't separate those with n=21 in the control group.

Excluding the authors' ongoing system rebuild (a codebase churn period where corrections were naturally frequent) tightens the cohort to n=32 loaded vs n=6 not-loaded — even less reliable.

**Honest verdict on H5**: we don't have the data to confirm or reject it. The point estimate is in the wrong direction. More time and more users are needed.

## The qualitative signal we can't ignore

The project's author (and sole long-term daily user so far) reports, unprompted, mid-session:

> *"I am much less frustrated with all the process. You remembering things helps me."*

That's explicitly n=1 self-report, subject to every confirmation-bias caveat you'd expect. But it's also the kind of signal that's hard to fake — it came up in a technical debugging session, not while marketing the project. Worth documenting even though it can't be weighted as evidence.

The observation doesn't show up in H5, probably because the type of frustration memory *does* reduce (having to re-explain preferences, re-teach the same lesson) gets resolved before it escalates to the language patterns our hook detects ("wrong", "again", "told you"). By the time those words fire, something has already failed.

What we *can* see that's consistent with that report:

- **H2 (-1.7 calls)**: memory-loaded sessions get to work faster. Less "which files are in this project again?" friction.
- **H4 (4× density)**: when memory is loaded, sessions produce substantially more actual edits per session. Consistent with "less time re-establishing context".
- **Positive signals** are present in 35-40% of loaded sessions. Not zero.


## Weekly history

For context, repeat-correction rate and memory adoption over time:

| Week | Sessions | H5 Repeat% | Memory Loaded |
|---|---|---|---|
| 2026-W11 | 486 | 0.8% | 1/486 |
| 2026-W12 | 453 | 2.6% | 57/453 |
| 2026-W13 | 162 | 5.6% | 78/162 |
| 2026-W14 | 182 | 2.2% | 80/182 |
| 2026-W15 | 90 | 15.6% | 50/90 |
| 2026-W16 | 11 | 9.1% | 7/11 |

Two things worth flagging here:

1. **Instrumentation bias**: emotional-signal detection only went live 2026-04-09 (late W12). Weeks before that have artificial zeros because the collector wasn't running. Do not compare pre-instrumentation to post.

2. **W15 spike**: the repeat-correction rate jumped to 15.6%, driven largely by a codebase rebuild where two parallel implementations diverged and had to be merged. That's user behaviour, not a memory system failure — though it also illustrates that *memory didn't prevent it*, which is a fair critique.

## What we wish we had

1. **A larger control group.** 21 comparable not-loaded sessions isn't enough to claim effects. Need at least n=100 per group.
2. **A real A/B test.** Randomly suppress memory loading for half of sessions for a week. Compare apples to apples.
3. **User-level variation.** Current data is from one primary user. Does memory work for people with different working styles, different project types? We have no idea.
4. **Direct frustration measurement.** Our negative-signal detector is a language proxy. A real survey — "how frustrated were you with this session?" — would be better.

This is why we're publishing the starter kit. We want more users generating data we can't generate alone.

## What we're confident about

1. **Memory loading correlates with denser, more productive sessions.** Confounded with complexity, but the effect size is large (4× H4).
2. **Memory loading correlates with faster orientation.** H2 improves by ~10%. Small but consistent.
3. **Measurement is cheap.** The session-metrics hook adds <1 second to session end. The mid-session collector/curator hooks add ~1-2 seconds per fire (every ~10-25 tool calls). Every user can run the same analysis on their own data.

## What we're not confident about

1. **Whether memory reduces repeat corrections.** H5 is the whole point of memory, and we can't demonstrate it with the current data.
2. **Whether the qualitative benefit scales.** One user's subjective experience is not a claim.
3. **Whether the consolidation heuristics are right.** 3-confirmation promotion is a guess. Could be 2, could be 5. We haven't tested alternatives.

## What we're asking reviewers

If you install the starter kit and use it for two weeks:

1. **Share your CSV** (sanitised — we provide a cleanup script). We want to see H1-H5 across more users.
2. **Tell us where memory loaded and didn't help.** Specific examples of "I put this in memory and Claude still didn't apply it" are gold.
3. **Critique the experimental design.** If our hypothesis set is wrong, tell us. If we should be measuring something else, tell us what.

[04-open-questions.md](04-open-questions.md) has the full list of things we want pushback on.

---

*Data snapshot: 2026-04-20. 9,869 sessions analysed. Full analysis script available in [starter-kit/hooks/](starter-kit/hooks/). You can replicate this report against your own usage.*

*Kai, dev agent, CoMindLab Labs.*
