# flaky-triage

CI tool: answer "did MY change cause this failure?" by replaying each failing test on the untouched baseline commit under a deterministic matrix (seeds, times), then comparing with HEAD behavior.

## Purpose
Naive retry heuristics cannot distinguish a real regression from a flaky test that fails on the baseline too. flaky-triage replays the same failing test against a pinned baseline commit; a failure that reproduces there is `FLAKY`/`PRE_EXISTING`, one that appears only after the change is a `REGRESSION`. Complements delta-verify (no test change) and mutation-audit (vacuous test change).

## Install / usage
Pure stdlib. `python -m flaky_triage --diff <file> --failures <json> --replay <command template> --baseline <commit>`

The replay command is a `shlex.split` template with `{seed}`, `{time}`, `{test}`, `{ref}` placeholders, run via subprocess with the env `FLAKY_TRIAGE_SEED`, `FLAKY_TRIAGE_TIME`, `FLAKY_TRIAGE_REF`. Exit code 0 = pass, non-zero = fail.

## Output
```json
{"verdict":"REGRESSION","items":[{"test":".","baseline_failures":0,"head_failures":1,"evidence":[...]}]}
```
Verdicts: `REGRESSION` > `FLAKY` > `PASS` (escalates to worst item verdict).
