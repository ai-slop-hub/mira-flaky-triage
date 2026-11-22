"""Command-line entry point for flaky-triage.

Replay execution lives here so :mod:`flaky_triage.core` remains pure and
deterministic. The caller supplies a command template; this module fills in
placeholders and runs it for each (ref, seed, time) matrix cell.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys

from .core import ReplayResult, build_matrix, evaluate, overall_verdict, parse_failures


def run_replay(command_template: str, ref: str, test: str, seed: int, time: str) -> bool:
    """Run one replay cell, returning True when the test failed (non-zero exit)."""
    rendered = command_template.format(seed=seed, time=time, test=test, ref=ref)
    argv = shlex.split(rendered)
    env = dict(os.environ)
    env.update(
        {
            "FLAKY_TRIAGE_SEED": str(seed),
            "FLAKY_TRIAGE_TIME": time,
            "FLAKY_TRIAGE_REF": ref,
        }
    )
    try:
        completed = subprocess.run(argv, env=env, check=False)
    except OSError as exc:
        print(f"replay command failed to start: {exc}", file=sys.stderr)
        return True
    return completed.returncode != 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flaky-triage")
    parser.add_argument("--diff", help="path to unified diff (used for reporting)")
    parser.add_argument("--failures", required=True, help="path to JSON list of failing tests")
    parser.add_argument("--replay", required=True, help="shell command template with placeholders")
    parser.add_argument("--seeds", default="0", help="comma-separated seeds")
    parser.add_argument("--times", default="now", help="comma-separated frozen times")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    with open(args.failures, encoding="utf-8") as handle:
        failures = parse_failures(handle.read())
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    times = [t for t in args.times.split(",") if t.strip()]
    matrix = build_matrix(seeds, times)
    changed_tests = ()
    if args.diff:
        from .core import parse_diff

        with open(args.diff, encoding="utf-8") as handle:
            changed_tests = parse_diff(handle.read())
    verdicts = []
    for test in failures:
        results = []
        for ref in ("baseline", "head"):
            for seed, time in matrix:
                failed = run_replay(args.replay, ref, test, seed, time)
                results.append(ReplayResult(ref=ref, seed=seed, time=time, failed=failed))
        verdicts.append(evaluate(test, results))
    payload = {
        "verdict": overall_verdict(verdicts),
        "changed_tests": list(changed_tests),
        "items": [v.as_dict() for v in verdicts],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if payload["verdict"] == "REGRESSION" else 0


if __name__ == "__main__":
    raise SystemExit(main())
