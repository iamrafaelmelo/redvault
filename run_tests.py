"""Run every test module in its own interpreter.

``app.config`` reads ``REDVAULT_DATA`` at import time and the platform modules
deliberately point it at different temporary databases. In one interpreter the
first module imported wins, so a full-suite run would silently test one module
against another module's database. This runner executes each test file in a
fresh process and aggregates the results.

    python3 run_tests.py            # everything
    python3 run_tests.py tests/test_labs.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TESTS = ROOT / "tests"


def modules() -> list[Path]:
    return sorted(
        path
        for path in TESTS.glob("test_*.py")
        if path.name != "conftest.py"
    )


def main(argv: list[str]) -> int:
    targets = [Path(arg) for arg in argv] or modules()
    failed = 0
    total = 0
    for target in targets:
        print(f"\n=== {target.name}", flush=True)
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", str(target), "-q", "-p", "no:cacheprovider"],
            cwd=str(ROOT),
        )
        if completed.returncode != 0:
            failed += 1
        else:
            total += 1
    print(f"\n{total}/{len(targets)} modules passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))