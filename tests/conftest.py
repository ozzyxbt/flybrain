import json
from pathlib import Path

import pytest

from flybrain.choice import manifest as mm
from flybrain.commitments.canonical import file_sha256, write_canonical

ROOT = Path(__file__).resolve().parents[1]
GENESIS = ROOT / "manifests" / "genesis-v1.json"
FIXTURE_CHECKPOINT = ROOT / "manifests" / "fixture-checkpoint-v1.json"


def small_manifest(checkpoint_path, **overrides):
    """A tiny valid manifest (two candidates per category) for fast tests."""
    base = json.loads(GENESIS.read_text())
    m = {**base, "manifest_id": "test-small", "brain_checkpoint_sha256": file_sha256(checkpoint_path)}
    cats = {
        "name": [{"id": "n-a", "text": "FLY"}, {"id": "n-b", "text": "PROBOSCIS"}],
        "ticker": [{"id": "t-a", "text": "FLY"}, {"id": "t-b", "text": "NEURON"}],
        "logo": base["categories"]["logo"][:2],
        "palette": base["categories"]["palette"][:2],
        "description": [
            {"id": "d-a", "text": "A FLY BRAIN CHOSE THIS COIN FROM A LIST. THE CHAIN KEEPS THE RECEIPTS."},
            {"id": "d-b", "text": "FLIES."},
        ],
        "launch_venue": base["categories"]["launch_venue"],
        "launch_action": base["categories"]["launch_action"],
    }
    m["categories"] = cats
    m.update(overrides)
    return m


def write_manifest(tmp_path, m, name="manifest.json"):
    path = tmp_path / name
    write_canonical(path, mm.validate(m))
    return path


def write_fixture_checkpoint(tmp_path, **params):
    base = json.loads(FIXTURE_CHECKPOINT.read_text())
    base.update({k: str(v) for k, v in params.items()})
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "fixture-checkpoint.json"
    path.write_text(json.dumps(base, indent=2) + "\n")
    return path


@pytest.fixture
def small_run(tmp_path):
    """Run the small manifest on the fixture brain and return (out_dir, summary)."""
    from flybrain.run import run

    cp = write_fixture_checkpoint(tmp_path)
    mpath = write_manifest(tmp_path, small_manifest(cp))
    out = tmp_path / "run"
    summary = run(mpath, cp, out, run_id="test-run", log=lambda *_: None)
    return out, summary
