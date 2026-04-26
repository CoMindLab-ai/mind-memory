# MindMemory

> A regenerable, navigable index of your structured Claude Code memory.

MindMemory walks your rules files and working-memory decisions, and writes a single `INDEX.md` you can scan in five seconds. It runs weekly via a SessionStart hook — zero manual upkeep.

This is a self-contained drop-in folder. Sibling to `starter-kit/` in the [MindMemory research repo](../README.md). Copy it into your project, run `/memory-index`, done.

## What it does

- Reads `memory/rules/*.md` — one rule per file, title from the first `# Heading`
- Reads `memory/working-memory.md` — bullets under `### Key Decisions`
- Writes `memory/INDEX.md` — flat sorted list, clickable file links, dates on decisions
- Re-runs once per 7 days via Claude Code's `SessionStart` hook (background spawn, never blocks)

## What it does NOT do

- No bidirectional `[[wiki-links]]` injected into your source files (link rot at scale)
- No graph visualisation
- No LLM calls — pure Python stdlib
- No clustering at small N — flat lists are honest until you cross ~50 entries
- No network calls

## Install

```bash
cp -r MindMemory/. your-project/
cd your-project
claude
> /memory-index
```

The wizard asks four questions (with defaults), writes `config/memory_index.config.json`, registers the SessionStart hook, and runs the first generation.

See [INSTALL.md](INSTALL.md) for the manual install path.

## Anatomy

```
MindMemory/
├── README.md
├── INSTALL.md
├── ARCHITECTURE.md
├── LICENSE
├── .claude/
│   ├── settings.json.example
│   ├── hooks/
│   │   └── memory-index-weekly.py     # SessionStart gate
│   └── skills/
│       └── memory-index.md            # Wizard skill
├── tools/
│   └── memory_index_generate.py       # The generator
├── memory/
│   ├── INDEX.md.example
│   ├── working-memory.md.example
│   └── rules/                         # Drop your *.md rules here
└── config/
    └── memory_index.config.example.json
```

## Run it manually

```bash
python tools/memory_index_generate.py            # write INDEX.md
python tools/memory_index_generate.py --dry-run  # preview to stdout
```

## Kill clause

This feature is on probation. If you have not opened `memory/INDEX.md` within four weeks of installing, delete the folder. An index nobody reads is worse than no index — it rots and lies.

## License

MIT — see [LICENSE](LICENSE).

---

*Part of the [MindMemory](../README.md) research preview, CoMindLab Labs 2026.*
