import pytest

from flaky_triage.core import (
    ReplayResult,
    build_matrix,
    classify,
    evaluate,
    overall_verdict,
    parse_diff,
    parse_failures,
)


def _res(ref, failed, seed=0, time="now"):
    return ReplayResult(ref=ref, seed=seed, time=time, failed=failed)


def test_classify_baseline_flaky():
    assert classify(1, 1) == "FLAKY"
    assert classify(2, 0) == "FLAKY"


def test_classify_regression_only_on_head():
    assert classify(0, 1) == "REGRESSION"


def test_classify_clean_pass():
    assert classify(0, 0) == "PASS"


def test_build_matrix_cartesian_order():
    assert build_matrix([1, 2], ["t0", "t1"]) == (
        (1, "t0"), (1, "t1"), (2, "t0"), (2, "t1")
    )


def test_parse_diff_only_test_files():
    diff = "--- a/app.py\n+++ b/app.py\n--- a/tests/test_x.py\n+++ b/tests/test_x.py\n"
    assert parse_diff(diff) == ("tests/test_x.py",)


def test_parse_failures_list_and_mapping():
    assert parse_failures('["b", "a", "b"]') == ("a", "b")
    assert parse_failures('{"tests": ["z"]}') == ("z",)


def test_regression_fails_only_on_head():
    v = evaluate("t", [_res("baseline", False), _res("head", True)])
    assert v.verdict == "REGRESSION"
    assert v.baseline_failures == 0
    assert v.head_failures == 1
    # evidence is a LIST of dicts, never a dict-as-key
    assert isinstance(v.evidence, tuple)
    assert all(isinstance(e, dict) for e in v.evidence)
    assert json_roundtrip(v)


def test_flaky_fails_on_baseline_too():
    v = evaluate("t", [_res("baseline", True), _res("head", True)])
    assert v.verdict == "FLAKY"
    assert v.baseline_failures == 1
    assert json_roundtrip(v)


def test_overall_escalates_to_worst_verdict():
    a = evaluate("a", [_res("baseline", False), _res("head", False)])
    b = evaluate("b", [_res("baseline", True), _res("head", True)])
    c = evaluate("c", [_res("baseline", False), _res("head", True)])
    assert overall_verdict([a]) == "PASS"
    assert overall_verdict([a, b]) == "FLAKY"
    assert overall_verdict([a, b, c]) == "REGRESSION"


def json_roundtrip(v):
    import json
    return json.loads(json.dumps(v.as_dict())) == v.as_dict()
