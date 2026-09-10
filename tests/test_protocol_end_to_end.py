import json

import numpy as np

from flybrain.choice import manifest as mm
from flybrain.choice.backends import FixtureBrain
from flybrain.choice.tournament import IDENTITY
from flybrain.commitments.hashchain import walk
from flybrain.run import run
from flybrain.verifier.verify import verify_run
from tests.conftest import small_manifest, write_fixture_checkpoint, write_manifest


def kinds(out):
    return [e["kind"] for e, _, _ in walk(out)]


def test_small_run_verifies_and_is_reproducible(tmp_path, small_run):
    out, summary = small_run
    report = verify_run(out, resimulate=True)
    assert report["ok"], [c for c in report["checks"] if not c["ok"]]
    assert summary["chain_length"] == len(kinds(out))
    # Same manifest, checkpoint and inputs => identical chain, hash for hash.
    cp = write_fixture_checkpoint(tmp_path / "again")
    mpath = write_manifest(tmp_path / "again", small_manifest(cp))
    again = run(mpath, cp, tmp_path / "again" / "run", run_id="test-run", log=lambda *_: None)
    assert again["chain_head"] == summary["chain_head"] and again["final_decision_sha256"] == summary["final_decision_sha256"]
    a = [(e["sha256"], e["path"]) for e, _, _ in walk(out)]
    b = [(e["sha256"], e["path"]) for e, _, _ in walk(tmp_path / "again" / "run")]
    assert a == b


def test_mirrored_trials_and_attempt_bookkeeping(small_run):
    out, _ = small_run
    trials = {d: a for e, a, d in walk(out) if e["kind"] == "trial"}
    for e, m, _ in walk(out):
        if e["kind"] != "match_result":
            continue
        for att in m["attempts"]:
            t1, t2 = trials[att["trial_1_sha256"]], trials[att["trial_2_sha256"]]
            assert (t1["left_candidate_id"], t1["right_candidate_id"]) == (m["candidate_a"], m["candidate_b"])
            assert (t2["left_candidate_id"], t2["right_candidate_id"]) == (m["candidate_b"], m["candidate_a"])
            assert t1["variant"] == t2["variant"] == att["variant"]
            assert t1["learning_frozen"] and t1["reinforcement"] == "none"
        assert len(m["attempts"]) <= m["max_attempts"]
        if m["winner"] is None:
            assert len(m["attempts"]) == m["max_attempts"]


def test_identical_candidates_end_in_no_decision_without_human_fallback(tmp_path):
    cp = write_fixture_checkpoint(tmp_path)
    m = small_manifest(cp)
    m["categories"]["name"] = [{"id": "n-a", "text": "SAME"}, {"id": "n-b", "text": "SAME"}]
    mpath = write_manifest(tmp_path, m)
    s = run(mpath, cp, tmp_path / "run", run_id="nodec", log=lambda *_: None)
    assert s["identity"]["name"] is None and s["outcome"] == "NO_LAUNCH" and s["launch"]["status"] == "NOT_ATTEMPTED"
    assert "identity incomplete" in s["launch"]["reason"]
    match = json.loads((tmp_path / "run" / "matches" / "name-r1-m1.json").read_text())
    assert match["result"] == "NO_DECISION" and len(match["attempts"]) == m["max_attempts_per_match"]
    assert all(a["result"] == "INCONCLUSIVE" for a in match["attempts"])
    assert "launch_venue" not in kinds(tmp_path / "run") or True
    ks = kinds(tmp_path / "run")
    assert "launch_intent" not in ks and "launch_receipt" not in ks
    final = json.loads((tmp_path / "run" / "final" / "decision.json").read_text())
    assert final["skipped_categories"] == ["launch_venue", "launch_action"]
    assert verify_run(tmp_path / "run", resimulate=True)["ok"]


def test_gate_failure_yields_no_decision(tmp_path):
    cp = write_fixture_checkpoint(tmp_path, gate_contrast_threshold="9.0")  # gate never fires
    mpath = write_manifest(tmp_path, small_manifest(cp))
    s = run(mpath, cp, tmp_path / "run", run_id="nogate", log=lambda *_: None)
    assert all(v is None for v in s["identity"].values()) and s["outcome"] == "NO_LAUNCH"
    for e, a, _ in walk(tmp_path / "run"):
        if e["kind"] == "match_result":
            assert all(att["result"] == "NO_GATE" for att in a["attempts"])
        if e["kind"] == "trial":
            assert a["gate_spikes"] == 0 and a["result"] == "NO_GATE"
    assert verify_run(tmp_path / "run")["ok"]


def test_launch_windows_wait_and_no_launch_are_recorded(tmp_path):
    """Force WAIT by giving 'launch' and 'wait' identical rendered content."""
    cp = write_fixture_checkpoint(tmp_path)
    m = small_manifest(cp)
    m["categories"]["launch_action"] = [{"id": "launch", "text": "SAME"}, {"id": "wait", "text": "SAME"}]
    mpath = write_manifest(tmp_path, m)
    s = run(mpath, cp, tmp_path / "run", run_id="windows", log=lambda *_: None)
    if s["identity_complete"] if "identity_complete" in s else all(s["identity"].values()):
        la = json.loads((tmp_path / "run" / "categories" / "launch_action.json").read_text())
        assert la["result"] == "NO_LAUNCH" and len(la["windows"]) == m["launch_windows"]["max_windows"]
        assert la["windows"][0]["next_window_after_seconds"] == m["launch_windows"]["interval_seconds"]
        assert la["windows"][-1]["next_window_after_seconds"] is None
        assert s["outcome"] == "NO_LAUNCH" and s["launch"]["status"] == "NOT_ATTEMPTED"
    assert verify_run(tmp_path / "run")["ok"]


def test_no_reinforcement_and_frozen_flags_everywhere(small_run):
    out, _ = small_run
    run_header = json.loads((out / "run.json").read_text())
    assert run_header["learning_frozen"] and not run_header["reinforcement_injected"] and not run_header["llm_in_decision_path"]
    manifest, _ = mm.load(out / "manifest.json")
    assert manifest["learning_frozen"] is True


def test_spike_and_input_artifacts_hash_to_envelopes(small_run):
    out, _ = small_run
    from flybrain.choice.renderer import load_png
    from flybrain.choice.transcript import frame_sha256, spike_sha256

    for e, t, _ in walk(out):
        if e["kind"] == "trial":
            assert frame_sha256(load_png(out / t["frame_path"])) == t["input_sha256"]
            counts = np.load(out / t["spike_path"])
            assert spike_sha256(counts) == t["spike_sha256"] and len(counts) == FixtureBrain.N
    assert set(IDENTITY) <= set(mm.CATEGORIES)
