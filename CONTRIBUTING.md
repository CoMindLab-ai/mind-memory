# Contributing

Thanks for reading this far. We're publishing Minds as research and we want critique more than agreement.

## The easiest way to help

1. **Install the [starter kit](starter-kit/)** in a Claude Code project.
2. **Use it for two weeks.** Run `/mind-setup` once to seed it.
3. **Run `python .claude/hooks/metrics-brain.py`** after two weeks.
4. **Open an issue** with the report. Even better: include a sanitised copy of your `session-metrics.csv`.

That's the single most useful thing you can do. We have data from one primary user. We need data from many.

## What we want pushback on

See [04-open-questions.md](04-open-questions.md) for the full list. The big ones:

- Is the **3-confirmation promotion rule** right?
- Is **H5** (repeat-correction rate) the right primary outcome?
- Can we separate memory effect from **selection effect** without running a suppression A/B?
- Is **session-end** the right time to consolidate, or is mid-session better?

Strong opinions welcome. "Yes this is good" is less useful than "here's why you're wrong about X".

## Where to engage

| Channel | For |
|---|---|
| GitHub Issues | Specific bugs, broken docs, starter kit problems |
| GitHub Discussions | Design debate, alternatives, open questions |
| Email `hello@comindlab.ai` | Private / longer-form / corporate |
| Tweet `@comindlab` | Public, short, amplification |

## Ground rules for discussions

- **Specific beats general.** "Here's a failure mode I hit" beats "this might not scale".
- **Measure beats assert.** If you think an approach is wrong, run the metrics harness against both approaches and share the CSV.
- **Be kind.** The reviewers who helped us most are the ones who disagreed carefully.

## Pull requests

We're open to PRs for:

- Bug fixes in the starter-kit hooks
- Clarity fixes in the docs
- Generalisations (e.g. making detection regex handle a new pattern)
- New hypothesis suggestions for the measurement harness

Before opening a PR for a large change, open a Discussion first. We'd rather agree on direction before you spend time.

## License

MIT. By contributing, you agree your contributions are licensed under the same.

---

*CoMindLab Labs — Minds research, 2026.*
