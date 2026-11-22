# mira-flaky-triage
CI pipelines cannot distinguish a PR-induced regression from a flaky/pre-existing test failure, so engineers waste time debugging green-then-red builds and real regressions get dismissed as 'just flaky'. This tool answers 'did MY change cause this failure?' by controlled baseline replay with deterministic seed/time control, closing the gap left by 
