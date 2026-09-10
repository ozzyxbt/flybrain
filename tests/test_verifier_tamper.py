"""One-bit modification to any artifact must fail `flybrain verify-run`."""

import json
from pathlib import Path

import numpy as np
import pytest

from flybrain.cli import main
from flybrain.verifier.verify import verify_run


def flip_bit(path: Path, offset=-1):
    data = bytearray(path.read_bytes())
    data[offset] ^= 0x01
    path.write_bytes(bytes(data))


def failed(report):
    return [c["check"] for c in report["checks"] if not c["ok"]]


def test_valid_fixture_passes_via_cli(small_run, capsys):
    out, _ = small_run
    assert main(["verify-run", str(out), "--resimulate"]) == 0
    assert "OK:" in capsys.readouterr().out


def test_tamper_png_pixel(small_run):
    out, _ = small_run
    from flybrain.choice.renderer import load_png, save_png

    p = next((out / "frames").glob("*.png"))
    frame = load_png(p)
    frame[100, 100, 0] ^= 1
    save_png(frame, p)
    r = verify_run(out)
    assert not r["ok"] and any("input_hash" in c for c in failed(r))


def test_tamper_spike_array(small_run):
    out, _ = small_run
    p = next((out / "spikes").glob("*.npy"))
    counts = np.load(p)
    counts[0] += 1
    np.save(p, counts)
    r = verify_run(out)
    assert not r["ok"] and any("spike_hash" in c for c in failed(r))


def test_tamper_manifest_byte(small_run):
    out, _ = small_run
    flip_bit(out / "manifest.json", 10)
    r = verify_run(out)
    assert not r["ok"]


def test_tamper_manifest_reorder_candidates(small_run):
    out, _ = small_run
    from flybrain.commitments.canonical import load_canonical, write_canonical

    m, _ = load_canonical(out / "manifest.json")
    m["categories"]["name"].reverse()
    write_canonical(out / "manifest.json", m)
    (out / "manifest.sha256").write_text(__import__("flybrain.commitments.canonical", fromlist=["canonical_sha256"]).canonical_sha256(m) + "\n")
    r = verify_run(out)
    assert not r["ok"] and any("run.manifest_hash" in c for c in failed(r))


def test_tamper_checkpoint(small_run):
    out, _ = small_run
    flip_bit(next((out / "checkpoint").iterdir()))
    r = verify_run(out)
    assert not r["ok"] and "checkpoint.hash_matches_manifest" in failed(r)


def test_tamper_trial_result_field(small_run):
    out, _ = small_run
    p = next((out / "trials").glob("*.json"))
    t = json.loads(p.read_text())
    t["left_hz"] = "999.000000"
    from flybrain.commitments.canonical import write_canonical

    write_canonical(p, t)
    r = verify_run(out)
    assert not r["ok"] and any("hash mismatch" in c["detail"].lower() for c in r["checks"] if not c["ok"])


def test_tamper_match_winner(small_run):
    out, _ = small_run
    from flybrain.commitments.canonical import canonical_bytes

    # Rewrite a match and re-index the chain to the tampered bytes: the
    # recomputed score must still expose the substitution.
    p = next((out / "matches").glob("*.json"))
    m = json.loads(p.read_text())
    if m["winner"] is None:
        pytest.skip("no decided match in this run")
    other = m["candidate_b"] if m["winner"] == m["candidate_a"] else m["candidate_a"]
    m["winner"] = other
    m["result"] = other
    data = canonical_bytes(m)
    p.write_bytes(data)
    import hashlib

    new = hashlib.sha256(data).hexdigest()
    lines = (out / "chain.jsonl").read_text().splitlines()
    rel = str(p.relative_to(out))
    fixed = []
    for line in lines:
        e = json.loads(line)
        if e["path"] == rel:
            e["sha256"] = new
        fixed.append(json.dumps(e, separators=(",", ":")))
    (out / "chain.jsonl").write_text("\n".join(fixed) + "\n")
    r = verify_run(out)
    assert not r["ok"]


def test_tamper_receipt_or_final(small_run):
    out, _ = small_run
    target = out / "launch" / "receipt.json"
    if not target.exists():
        target = out / "final" / "decision.json"
    flip_bit(target, 5)
    r = verify_run(out)
    assert not r["ok"]


def test_chain_truncation_and_reorder(small_run):
    out, _ = small_run
    lines = (out / "chain.jsonl").read_text().splitlines()
    (out / "chain.jsonl").write_text("\n".join(lines[:-1]) + "\n")
    assert not verify_run(out)["ok"]
    (out / "chain.jsonl").write_text("\n".join([lines[0], lines[2], lines[1]] + lines[3:]) + "\n")
    assert not verify_run(out)["ok"]


def test_missing_frame_fails(small_run):
    out, _ = small_run
    next((out / "frames").glob("*.png")).unlink()
    assert not verify_run(out)["ok"]
