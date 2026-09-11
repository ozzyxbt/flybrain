"""The audit bundles committed under fixtures/runs/ must verify, and the
current code must reproduce every protocol-level result from the committed
manifests: same inputs, spikes, rates, scores, winners, outcome."""

import json
from pathlib import Path

import pytest

from flybrain.commitments.hashchain import walk
from flybrain.run import run
from flybrain.verifier.verify import verify_run

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = sorted((ROOT / "fixtures" / "runs").glob("*/")) if (ROOT / "fixtures" / "runs").exists() else []

# run.json carries the software identity (git commit), so its hash and every
# chain-derived hash after it legitimately differ between code versions. The
# protocol content must not.
CHAIN_DERIVED = {"previous_sha256", "chain_seq", "category_roots", "mint", "signature", "expected_mint", "unsigned", "intent_id", "final_decision_sha256", "intent_sha256", "receipt_sha256", "trial_1_sha256", "trial_2_sha256", "match_sha256", "sha256", "software"}
KEPT_HASHES = {"input_sha256", "spike_sha256", "checkpoint_sha256", "manifest_sha256", "logo_png_sha256"}


def protocol_view(value):
    if isinstance(value, dict):
        return {k: protocol_view(v) for k, v in value.items() if k in KEPT_HASHES or (k not in CHAIN_DERIVED and not k.endswith("_sha256"))}
    if isinstance(value, list):
        return [protocol_view(v) for v in value]
    return value


@pytest.mark.parametrize("bundle", FIXTURES, ids=[b.name for b in FIXTURES])
def test_committed_bundle_verifies_and_reproduces(bundle, tmp_path):
    report = verify_run(bundle, resimulate=True)
    assert report["failures"] == 0, [c for c in report["checks"] if not c["ok"]]
    header = json.loads((bundle / "run.json").read_text())
    manifest = ROOT / "manifests" / f"{header['manifest_id']}.json"
    run(manifest, ROOT / "manifests" / "fixture-checkpoint-v1.json", tmp_path / "rerun", run_id=header["run_id"], log=lambda *_: None)
    committed = [(e["kind"], e["path"], protocol_view(a)) for e, a, _ in walk(bundle)]
    fresh = [(e["kind"], e["path"], protocol_view(a)) for e, a, _ in walk(tmp_path / "rerun")]
    assert committed == fresh
    assert verify_run(tmp_path / "rerun", resimulate=True)["failures"] == 0
