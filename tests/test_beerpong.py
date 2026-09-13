import json

import numpy as np

from flybrain.commitments.hashchain import walk
from flybrain.games import beerpong
from tests.conftest import write_fixture_checkpoint


def test_drunk_filter_degrades_input_deterministically():
    frame = beerpong.render_table([list(c) for c in beerpong.RULES["cups"]], 0)
    assert frame.shape == (180, 320, 3) and frame.dtype == np.uint8
    d1 = beerpong.drunk_filter(frame, 1)
    d3 = beerpong.drunk_filter(frame, 3)
    assert np.array_equal(beerpong.drunk_filter(frame, 1), d1)
    edge = lambda f: float(np.abs(np.diff(f.astype(float), axis=1)).mean())
    assert edge(d1) < edge(frame) and edge(d3) < edge(d1), "more drinks, less edge contrast"
    assert np.array_equal(beerpong.drunk_filter(frame, 0), frame)


def test_landing_and_hit_rule():
    assert beerpong.landing("30.000000", "36.000000") == "1.000000"
    assert beerpong.landing("36.000000", "30.000000") == "-1.000000"
    assert beerpong.landing("30.000000", "31.500000") == "0.250000"
    assert beerpong.landing("30.000000", "40.000000", "10.000000") == "0.000000", "bias measured on the empty table is subtracted"
    cups = [list(c) for c in beerpong.RULES["cups"]]
    assert beerpong.hit_test("0.250000", cups) == ["0.25", 1]
    assert beerpong.hit_test("0.100000", cups) == ["0", 0], "front row first"
    assert beerpong.hit_test("0.800000", cups) is None


def test_fixture_game_is_chained_reward_follows_hit_and_drinks_follow_misses(tmp_path):
    cp = write_fixture_checkpoint(tmp_path)
    s = beerpong.play("fixture-brain-v1", cp, tmp_path / "g", run_id="t", log=lambda *_: None)
    entries = list(walk(tmp_path / "g"))
    kinds = [e["kind"] for e, _, _ in entries]
    assert kinds[0] == "pong_header" and kinds[1] == "calibration" and kinds[-1] == "pong_result" and kinds.count("throw") == s["throws"]
    cal = next(a for e, a, _ in entries if e["kind"] == "calibration")
    assert cal["bias_hz"] == str(__import__("decimal").Decimal(cal["right_hz"]) - __import__("decimal").Decimal(cal["left_hz"]))
    throws = [a for e, a, _ in entries if e["kind"] == "throw"]
    prev_hit = False
    drinks = 0
    cups = len(beerpong.RULES["cups"])
    for a in throws:
        assert (a["reward_applied_ms"] > 0) == prev_hit, "reward pulse exactly on the throw after a hit"
        assert a["bias_hz"] == cal["bias_hz"] and a["landing_x"] == beerpong.landing(a["left_hz"], a["right_hz"], cal["bias_hz"])
        assert a["drinks_before"] == drinks and len(a["cups_before"]) == cups
        if a["hit"]:
            cups -= 1
            assert a["cup"] in a["cups_before"] and a["cup"] not in a["cups_after"]
        else:
            drinks += 1
        assert a["drinks_after"] == drinks and len(a["cups_after"]) == cups
        counts = np.load(tmp_path / "g" / a["spike_path"])
        assert __import__("hashlib").sha256(counts.astype("<i4").tobytes()).hexdigest() == a["spike_sha256"]
        prev_hit = a["hit"]
    assert s["hits"] + s["misses"] == s["throws"] and s["drinks"] == drinks and s["cups_left"] == cups
    # replaying the same game reproduces the same chain
    s2 = beerpong.play("fixture-brain-v1", cp, tmp_path / "g2", run_id="t", log=lambda *_: None)
    assert s2["chain_head"] == s["chain_head"]
    header = json.loads((tmp_path / "g" / "run.json").read_text())
    assert "not pleasure" in header["disclosure"] and header["reward_cells"] == 15
