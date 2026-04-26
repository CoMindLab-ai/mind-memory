# Install

Two paths: wizard (recommended) and manual.

## Wizard install

```bash
cp -r MindMemory/. your-project/
cd your-project
claude
> /memory-index
```

The wizard:

1. Detects whether `config/memory_index.config.json` exists.
2. If not, asks five questions with defaults:
   - Rules directory (default `memory/rules`)
   - Working memory file (default `memory/working-memory.md`)
   - Decisions section heading (default `Key Decisions`)
   - Output file (default `memory/INDEX.md`)
   - Register SessionStart hook? (default yes)
3. Writes the config.
4. Appends the hook entry to `.claude/settings.json` (or copies `settings.json.example` if missing).
5. Runs `python tools/memory_index_generate.py --dry-run` — you see the output before commit.
6. On your approval, runs without `--dry-run` and prints the final INDEX.md path.

## Manual install

If you prefer not to run the wizard:

```bash
# 1. Copy the folder
cp -r MindMemory/. your-project/
cd your-project

# 2. Copy the config
cp config/memory_index.config.example.json config/memory_index.config.json
# Edit paths if your layout differs from the defaults.

# 3. Wire the SessionStart hook
# If you have no .claude/settings.json yet:
cp .claude/settings.json.example .claude/settings.json
# Otherwise merge the SessionStart entry from settings.json.example into yours.

# 4. Seed your sources
# Drop your rules into memory/rules/ as individual .md files.
# Make sure your memory/working-memory.md has a `### Key Decisions` section.

# 5. Generate once to verify
python tools/memory_index_generate.py
cat memory/INDEX.md
```

## After install

The hook fires every Claude Code session start. It does nothing on most sessions — only regenerates `INDEX.md` if seven days have passed since the last run. The timestamp lives at `memory/.memory_index_last_run`.

To force a fresh regeneration immediately:

```bash
rm memory/.memory_index_last_run
python tools/memory_index_generate.py
```

To uninstall:

1. Remove the SessionStart hook entry from `.claude/settings.json`.
2. Delete the `MindMemory/` folder.

No other state to clean up.
