"""flaky-triage: distinguish PR-induced regressions from flaky failures via baseline replay."""

from .core import (
    ReplayResult,
    TestVerdict,
    build_matrix,
    classify,
    evaluate,
    overall_verdict,
    parse_diff,
    parse_failures,
)

__all__ = [
    "ReplayResult",
    "TestVerdict",
    "build_matrix",
    "classify",
    "evaluate",
    "overall_verdict",
    "parse_diff",
    "parse_failures",
]
