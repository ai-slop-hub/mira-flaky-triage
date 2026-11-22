"""Core logic for flaky-triage.

No git/subprocess I/O lives here: callers supply replay results so the
classification logic is fully deterministic and unit-testable. All public
containers are plain dataclasses and the aggregation helpers return only
immutable built-in types (no dict keys that are themselves dicts).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class ReplayResult:
    """Outcome of replaying one test under one matrix cell.

    Attributes:
        ref: git ref replayed ("baseline" or "head").
        seed: RNG seed used for this replay.
        time: frozen clock value (ISO-ish string) used for this replay.
        failed: True when the replay command exited non-zero.
    """

    ref: str
    seed: int
    time: str
    failed: bool

    def as_dict(self) -> dict:
        """Return a JSON-serializable representation."""
        return {"ref": self.ref, "seed": self.seed, "time": self.time, "failed": self.failed}


@dataclass(frozen=True)
class TestVerdict:
    """Classification for a single test.

    ``evidence`` holds ``ReplayResult.as_dict()`` dictionaries (lists of
    scalar-keyed dicts), never dicts used as mapping keys.
    """

    test: str
    verdict: str
    baseline_failures: int
    head_failures: int
    evidence: tuple[dict, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict:
        """Return a JSON-serializable representation."""
        return {
            "test": self.test,
            "verdict": self.verdict,
            "baseline_failures": self.baseline_failures,
            "head_failures": self.head_failures,
            "evidence": list(self.evidence),
        }


def parse_diff(diff_text: str) -> tuple[str, ...]:
    """Extract changed test file paths from a unified diff.

    Args:
        diff_text: raw unified diff.

    Returns:
        Sorted unique paths that look like test files.
    """
    paths: set[str] = set()
    for line in diff_text.splitlines():
        if not line.startswith("+++ "):
            continue
        path = line[4:].strip()
        if path == "/dev/null":
            continue
        normalized = path[2:] if path.startswith("b/") else path
        if "test" in normalized.lower():
            paths.add(normalized)
    return tuple(sorted(paths))


def parse_failures(failures_json: str) -> tuple[str, ...]:
    """Parse a JSON list (or a mapping with a ``tests`` key) of failing tests.

    Args:
        failures_json: JSON text describing failing tests.

    Returns:
        Sorted unique test identifiers.
    """
    import json

    data = json.loads(failures_json)
    if isinstance(data, dict):
        raw = data.get("tests", [])
    else:
        raw = data
    if not isinstance(raw, list):
        raise ValueError("failures must be a JSON list of test ids")
    return tuple(sorted({str(item) for item in raw}))


def build_matrix(seeds: Sequence[int], times: Sequence[str]) -> tuple[tuple[int, str], ...]:
    """Build the deterministic replay matrix as (seed, time) pairs.

    Args:
        seeds: integer RNG seeds.
        times: frozen clock values.

    Returns:
        Cartesian product in stable order.
    """
    return tuple((s, t) for s in seeds for t in times)


def classify(baseline_failures: int, head_failures: int) -> str:
    """Map failure counts into a verdict string.

    A failure reproducing on the untouched baseline is flaky/pre-existing;
    a failure appearing only on HEAD is a regression.
    """
    if head_failures > 0 and baseline_failures == 0:
        return "REGRESSION"
    if baseline_failures > 0:
        return "FLAKY"
    return "PASS"


_VERDICT_RANK = {"PASS": 0, "FLAKY": 1, "REGRESSION": 2}


def evaluate(
    test: str,
    results: Iterable[ReplayResult],
) -> TestVerdict:
    """Aggregate replay results for one test into a :class:`TestVerdict`.

    Args:
        test: test identifier.
        results: replay results across baseline and HEAD matrix cells.

    Returns:
        A verdict with scalar failure counts and list-of-dict evidence.
    """
    baseline_failures = 0
    head_failures = 0
    evidence: list[dict] = []
    for result in results:
        if result.failed:
            if result.ref == "baseline":
                baseline_failures += 1
            elif result.ref == "head":
                head_failures += 1
        evidence.append(result.as_dict())
    verdict = classify(baseline_failures, head_failures)
    return TestVerdict(
        test=test,
        verdict=verdict,
        baseline_failures=baseline_failures,
        head_failures=head_failures,
        evidence=tuple(evidence),
    )


def overall_verdict(verdicts: Iterable[TestVerdict]) -> str:
    """Escalate to the worst verdict across all evaluated tests."""
    worst = "PASS"
    for item in verdicts:
        if _VERDICT_RANK[item.verdict] > _VERDICT_RANK[worst]:
            worst = item.verdict
    return worst
