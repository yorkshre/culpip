from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .core import BaselineError, find_culprits
from .parse import load
from .runner import run_trial


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="culpip",
        description="Find which dependency update broke your tests.",
    )
    p.add_argument("--good", required=True, type=Path, help="pinned requirements or uv.lock that passes")
    p.add_argument("--bad", required=True, type=Path, help="pinned requirements or uv.lock that fails")
    p.add_argument("--test", required=True, help='test command, e.g. "pytest -x"')
    p.add_argument("--project", type=Path, default=Path("."), help="project dir (default: .)")
    p.add_argument("--editable", action="store_true", help="also install the project (-e)")
    p.add_argument("--version", action="version", version=f"culpip {__version__}")
    args = p.parse_args(argv)

    try:
        good = load(args.good.read_text(), args.good.name)
        bad = load(args.bad.read_text(), args.bad.name)
        result = find_culprits(
            good,
            bad,
            lambda lines: run_trial(lines, args.test, args.project, args.editable),
            log=lambda m: print(m, file=sys.stderr),
        )
    except (BaselineError, ValueError, OSError) as e:
        print(f"culpip: {e}", file=sys.stderr)
        return 2

    print()
    label = "Culprit" if len(result.culprits) == 1 else "Culprits (fail only together)"
    print(f"{label}:")
    for c in result.culprits:
        print(f"  {c}")
    print(f"\n{result.trials} trials, {result.errors} could not be built.")
    return 0
