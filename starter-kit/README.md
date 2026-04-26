# CognitiveMemory Starter Kit

The drop-in memory layer for [Claude Code](https://claude.com/claude-code).

## What's in the box

```
.claude/
  hooks/
    session-metrics.py       Captures session data on SessionEnd
    metrics-brain.py         Weekly analyser — writes daily-report.md
  skills/
    cognitive-memory-setup.md  Interactive setup wizard
  settings.json.example      Hook wiring (rename or merge into yours)
memory/
  MEMORY.md                  Long-term memory index
  working-memory.md          This week's context
CLAUDE.md                    Project conventions + memory loader
```

## Install

### Option A — Fresh project (no existing `.claude/`)

```bash
# From the repo root
cp -r starter-kit/. your-project/
cd your-project
mv .claude/settings.json.example .claude/settings.json
claude
> /cognitive-memory-setup
```

Two commands + the wizard. Under 5 minutes.

### Option B — Existing Claude Code project

You probably already have `.claude/settings.json` and a `CLAUDE.md`. Don't overwrite them.

Copy everything from the starter kit except `settings.json.example`:

```bash
cp starter-kit/.claude/hooks/*.py your-project/.claude/hooks/
cp starter-kit/.claude/skills/cognitive-memory-setup.md your-project/.claude/skills/
cp -r starter-kit/memory your-project/memory
```

Then merge the `hooks.SessionEnd` block from `starter-kit/.claude/settings.json.example` into your existing `.claude/settings.json` (see [merge guide](#merging-settingsjson)).

Add these two lines to your existing `CLAUDE.md`:

```markdown
Read memory/MEMORY.md for preferences, project lessons, and heuristics.
Read memory/working-memory.md for this week's context.
```

Then run `claude` and invoke `/cognitive-memory-setup`.

## Smoke test (30 seconds)

After install, verify the hook fires:

```bash
# 1. Start a Claude Code session
claude
# 2. Do one quick thing (e.g. ask it to list files)
> list the files in this directory
# 3. Exit the session (Ctrl+D or type `exit`)
# 4. Check the CSV got a row
cat .claude/metrics/session-metrics.csv
```

If the CSV has a header row + your session row, the hook is wired correctly.

If the file doesn't exist, the SessionEnd hook isn't firing. Check `.claude/settings.json` has the hook block and that `python` is in your PATH.

## Merging settings.json

If you already have `.claude/settings.json`:

### Your existing file

```json
{
  "permissions": { "allow": [...] }
}
```

### After merge

```json
{
  "permissions": { "allow": [...] },
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          { "type": "command", "command": "python .claude/hooks/session-metrics.py" }
        ]
      }
    ]
  }
}
```

If you already have `hooks.SessionEnd`, append the session-metrics entry to the existing array.

## What the wizard does

`/cognitive-memory-setup` walks you through two stages:

**Step 0 — Safety check** (only if you have existing CognitiveMemory files). The wizard scans `.claude/identity/` and `memory/` and asks how to handle anything it finds: **Overwrite**, **Backup then overwrite** (renames to `<name>.bak-{timestamp}`, recommended), **Skip existing**, or **Cancel**. Whatever you pick is honoured for every file.

**Quick path (default, ~5 min)** — seven questions via `AskUserQuestion`:

1. **Mind handle** — short lowercase name (`alex-dev`, `research-assistant`)
2. **Role** — one sentence about what this mind does
3. **Personality archetype** — craftsperson / operator / reviewer / creator / custom
4. **Hard rules** — 2-3 things this mind must never do
5. **Past mistakes to remember** — seeds the first memory entries
6. **Working style preferences** — brevity, tools, conventions
7. **About you** — multi-select accommodations (dyslexic, visual learner, ADHD, non-native English, colour-blind, experienced, new to domain, other). Skippable. Goes into a separate `user_profile.md` that influences formatting and pacing across every session — not a hard rule.

**Deep-dive path (opt-in, +10-15 min)** — after question 3 the wizard offers a deeper conversation. If you opt in, it switches from multiple-choice to free-form chat and asks open questions about how you want the mind to disagree, deliver bad news, what makes you proud of its work, words you never want to hear, etc. Then it drafts a 2-3 paragraph personality, shows it to you, and iterates until you say "save it." After approval it returns to questions 4-6.

When done, the wizard writes:

- `.claude/identity/anchor.md` — who this mind is (with the rich personality if you went deep)
- `memory/MEMORY.md` — index with your starter entries
- `memory/feedback_*.md` — one file per past-mistake entry
- `memory/working-memory.md` — current focus
- `memory/user_profile.md` — your accommodations, only if you answered question 7

Re-run any time to update — the safety check protects existing work.

**Prerequisite**: `AskUserQuestion` needs to be available in your Claude Code session. It should be by default in recent versions. If the wizard stalls on question 1, your Claude Code version may not have it — fall back to editing the memory files by hand (the templates are already self-explanatory).

## Measuring whether memory helps you

After two weeks of regular use:

```bash
python .claude/hooks/metrics-brain.py
cat .claude/metrics/daily-report.md
```

The report shows:

- **H1 Production ratio** — productive edits / total tool calls
- **H2 Orientation speed** — exploration calls before first edit (lower is better)
- **H3 Agent efficiency** — delegated calls / total calls
- **H4 Session density** — productive calls per session
- **H5 Repeat-correction rate** — % of sessions with repeated corrections (lower is better)

Plus a matched-cohort comparison: sessions with memory loaded vs not. If memory is helping you, the loaded group should show better H1/H2/H4 and lower H5.

Read [../03-findings.md](../03-findings.md) for what the data looked like in our 3-month test.

## Privacy

- All data stays local. No telemetry.
- The CSV is at `.claude/metrics/session-metrics.csv`. You own it.
- You can delete rows or the whole file at any time.

## Troubleshooting

| Symptom                              | Likely cause          | Fix                                                                              |
| ------------------------------------ | --------------------- | -------------------------------------------------------------------------------- |
| Hook doesn't fire                    | SessionEnd not wired  | Check `.claude/settings.json` has the hook block                                 |
| CSV has blank columns                | Old transcript format | Newer transcripts populate correctly — just keep using                           |
| `/cognitive-memory-setup` not found  | Skill not loaded      | Make sure `.claude/skills/cognitive-memory-setup.md` exists; restart `claude`    |
| Report says "not enough data"        | < 2 weeks of sessions | Keep using. Report needs ≥30 sessions/week for stable signal                     |
| `python: command not found`          | Python 3 not on PATH  | Replace `python` with `python3` in `settings.json`                               |

## Who should use this

- You use Claude Code daily and get frustrated re-teaching the same lessons
- You want structured, readable memory you can edit by hand
- You're OK with markdown files as your "database"

## Who should probably skip this

- You don't use Claude Code (this is CC-specific, not LLM-generic)
- You need enterprise audit trails for memory changes (this is markdown on disk)
- You want something with a UI — CognitiveMemory is files and CLI

## Contributing

See [../CONTRIBUTING.md](../CONTRIBUTING.md) and [../04-open-questions.md](../04-open-questions.md) for what we want feedback on.

---

*CognitiveMemory starter kit v0.1 — MIT — CoMindLab Labs*
