"""SessionStart hook — weekly MindMemory index regeneration.

Runs on every Claude Code session start. Gates by timestamp file: only
regenerates INDEX.md if the last run was more than 7 days ago. Spawns the
generator as a fire-and-forget background process so session start is never
blocked.

Cost when gate blocks: ~1ms (file stat). Cost when gate fires: <50ms (Popen).
Hook NEVER fails the session — all errors swallowed.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

WEEK_SECONDS = 7 * 24 * 3600

# Hook lives at <repo>/.claude/hooks/memory-index-weekly.py
# Generator lives at <repo>/tools/memory_index_generate.py
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GENERATOR = REPO_ROOT / "tools" / "memory_index_generate.py"
LAST_RUN = REPO_ROOT / "memory" / ".memory_index_last_run"


def main() -> int:
    if not GENERATOR.exists():
        return 0

    if LAST_RUN.exists():
        age = time.time() - LAST_RUN.stat().st_mtime
        if age < WEEK_SECONDS:
            return 0

    try:
        creationflags = 0
        if sys.platform == "win32":
            creationflags = 0x08000000  # CREATE_NO_WINDOW
        subprocess.Popen(
            [sys.executable, str(GENERATOR), "--repo-root", str(REPO_ROOT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        LAST_RUN.parent.mkdir(parents=True, exist_ok=True)
        LAST_RUN.touch()
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
