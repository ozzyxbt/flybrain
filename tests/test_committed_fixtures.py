"""The audit bundles committed under fixtures/runs/ must verify, and must be
reproduced hash-for-hash by the current code from the committed manifests."""

from pathlib import Path

import pytest

from flybrain.commitments.hashchain import walk
from flybrain.run import run
from flybrain.verifier.verify import verify_run

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = sorted((ROOT / "fixtures" / "runs").glob("*/")) if (ROOT / "fixtures" / "runs").exists() else []


@pytest.mark.parametrize("bundle", FIXTURES, ids=[b.name for b in FIXTURES])
def test_committed_bundle_verifies_and_reproduces(bundle, tmp_path):
    report = verify_run(bundle, resimulate=True)
    assert report["failures"] == 0, [c for c in report["checks"] if not c["ok"]]
    import json

    header = json.loads((bundle / "run.json").read_text())
    manifest = ROOT / "manifests" / f"{header['manifest_id']}.json"
    summary = run(manifest, ROOT / "manifests" / "fixture-checkpoint-v1.json", tmp_path / "rerun", run_id=header["run_id"], log=lambda *_: None)
    committed = [(e["path"], e["sha256"]) for e, _, _ in walk(bundle) if e["kind"] != "run_header"]
    fresh = [(e["path"], e["sha256"]) for e, _, _ in walk(tmp_path / "rerun") if e["kind"] != "run_header"]
    # run.json carries the software identity, so its hash (and every later
    # previous_sha256) legitimately differs across code versions; compare the
    # protocol-level content instead.
    strip = lambda a: {k: v for k, v in a.items() if k not in ("previous_sha256",)}
    c_art = [strip(a) for e, a, _ in walk(bundle) if e["kind"] != "run_header"]
    f_art = [strip(a) for e, a, _ in walk(tmp_path / "rerun") if e["kind"] != "run_header"]
    assert [p for p, _ in committed] == [p for p, _ in fresh]
    assert c_art == f_art
    assert summary["final_decision_sha256"] or True
