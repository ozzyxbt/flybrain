"""The retained Stonkfly neural core must stay byte-identical to the baseline
commit, except the two documented adaptations (data location, package path)."""

import hashlib
import json
from pathlib import Path

NEURAL = Path(__file__).resolve().parents[1] / "flybrain" / "neural"
ALLOWED_MODIFIED = {"common.py", "data.py"}


def test_retained_core_matches_recorded_baseline():
    record = json.loads((NEURAL / "BASELINE.json").read_text())
    assert record["baseline_commit"] == "78ef3e05ab0fa086032098558d893667068944a0"
    for name, info in record["files"].items():
        actual = hashlib.sha256((NEURAL / name).read_bytes()).hexdigest()
        assert actual == info["sha256"], f"{name} changed since BASELINE.json was recorded"
        if name in ALLOWED_MODIFIED:
            assert info["modified"] is True
        else:
            assert info["modified"] is False and info["sha256"] == info["upstream_sha256"], f"{name} must be identical to upstream"
    present = {p.name for p in NEURAL.iterdir() if p.suffix in (".py", ".cpp", ".json") and p.name != "BASELINE.json"}
    assert present == set(record["files"]), "unexpected files in the retained core"


def test_kernel_and_rule_are_the_baseline():
    record = json.loads((NEURAL / "BASELINE.json").read_text())
    assert record["files"]["kernel.cpp"]["upstream_sha256"] == "e2d4d584f4633613277bb1bf6ea7ba20855c01a332ae2e9344ed7782604c8509"
    assert record["files"]["brain.py"]["upstream_sha256"] == "895d0bcab7e03e859547e516905edc39fd2af4bb7ff7a7bf67d819bc15ac8c4d"
    assert record["files"]["rule.py"]["upstream_sha256"] == "3c80680450c3b73042e332bd7ce8289d7d74d8695c60e7ac19eefd9759d95c44"
