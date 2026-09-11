import json

import numpy as np

from flybrain.verifier.verify import verify_run


def test_run_header_binds_brain_atlas(small_run):
    out, _ = small_run
    run = json.loads((out / "run.json").read_text())
    assert run["atlas"]["path"] == "brain/atlas.json" and run["atlas"]["schematic"] is True
    atlas = json.loads((out / "brain" / "atlas.json").read_text())
    pos = np.frombuffer((out / "brain" / "positions.f32").read_bytes(), dtype="<f4").reshape(-1, 3)
    assert pos.shape == (atlas["n"], 3) == (64, 3) and np.isfinite(pos).all()
    assert atlas["cells"]["left"] == list(range(16)) and atlas["cells"]["gate"] == [32, 33, 34, 35]
    assert "schematic" in atlas["note"].lower() or atlas["schematic"] is True
    assert verify_run(out)["ok"]


def test_tampered_atlas_fails_verification(small_run):
    out, _ = small_run
    data = bytearray((out / "brain" / "positions.f32").read_bytes())
    data[3] ^= 1
    (out / "brain" / "positions.f32").write_bytes(bytes(data))
    r = verify_run(out)
    assert not r["ok"] and any(c["check"] == "atlas.positions_hash_and_size" for c in r["checks"] if not c["ok"])
