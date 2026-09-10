import numpy as np
import pytest

from flybrain.choice import decoder, manifest as mm, renderer
from flybrain.choice.backends import FixtureBrain
from tests.conftest import FIXTURE_CHECKPOINT, GENESIS


@pytest.fixture(scope="module")
def genesis():
    return mm.load(GENESIS)[0]


def test_render_is_deterministic_and_mirror_is_a_pure_swap(genesis):
    a, b = mm.candidates(genesis, "logo")[:2]
    f1 = renderer.render(genesis, "logo", a, b, "standard")
    f2 = renderer.render(genesis, "logo", a, b, "standard")
    m = renderer.render(genesis, "logo", b, a, "standard")
    assert f1.shape == (180, 320, 3) and f1.dtype == np.uint8
    assert np.array_equal(f1, f2)
    assert not np.array_equal(f1, m)
    lx0, lx1 = renderer.LEFT_CARD
    rx0, rx1 = renderer.RIGHT_CARD
    y0, y1 = renderer.CARD_Y0, renderer.CARD_Y1
    assert np.array_equal(f1[y0:y1, lx0:lx1], m[y0:y1, rx0:rx1]) and np.array_equal(f1[y0:y1, rx0:rx1], m[y0:y1, lx0:lx1])
    # Everything outside the two cards is identical between the two trials:
    # the only difference is which side each candidate is on.
    mask = np.ones((180, 320), bool)
    mask[y0:y1, lx0:lx1] = False
    mask[y0:y1, rx0:rx1] = False
    assert np.array_equal(f1[mask], m[mask])
    # And the card regions themselves are the same size on both sides.
    assert (lx1 - lx0) == (rx1 - rx0) and lx0 == 320 - rx1


def test_every_category_and_variant_renders(genesis):
    for cat in mm.CATEGORIES:
        cs = mm.candidates(genesis, cat)
        for v in genesis["attempt_variants"]:
            renderer.render(genesis, cat, cs[0], cs[1], v, "WINDOW 1/3" if cat == "launch_action" else "")
    with pytest.raises(ValueError):
        renderer.render(genesis, "logo", cs[0], cs[1], "neon")


def test_readout_and_score_rule():
    cells = {"left": np.array([0, 1]), "right": np.array([2, 3]), "gate": np.array([4])}
    r = decoder.readout(np.array([10, 10, 4, 4, 1]), cells, 500)
    assert r == {"left_hz": "20.000000", "right_hz": "8.000000", "gate_spikes": 1, "raw_side": "LEFT"}
    t1 = {"left_hz": "20.000000", "right_hz": "8.000000", "gate_spikes": 1}
    t2 = {"left_hz": "8.000000", "right_hz": "20.000000", "gate_spikes": 1}
    assert decoder.score(t1, t2, "2.0") == {"a_score": "12.000000", "b_score": "-12.000000", "result": "A"}
    assert decoder.score(t2, t1, "2.0")["result"] == "B"
    assert decoder.score(t1, {**t2, "gate_spikes": 0}, "2.0") == {"a_score": None, "b_score": None, "result": "NO_GATE"}
    assert decoder.score(t1, t1, "2.0")["result"] == "INCONCLUSIVE"  # left bias only


def test_persistent_side_bias_cancels_in_mirrored_score():
    bias = 3.0
    t1 = {"left_hz": f"{10 + bias:.6f}", "right_hz": "10.000000", "gate_spikes": 1}  # A left, no preference
    t2 = {"left_hz": f"{10 + bias:.6f}", "right_hz": "10.000000", "gate_spikes": 1}  # B left, same bias
    s = decoder.score(t1, t2, "2.0")
    assert s["a_score"] == "0.000000" and s["result"] == "INCONCLUSIVE"


def test_fixture_brain_is_deterministic_content_bound_and_biased(genesis):
    b = FixtureBrain(FIXTURE_CHECKPOINT)
    a, c = mm.candidates(genesis, "name")[:2]
    f = renderer.render(genesis, "name", a, c, "standard")
    x, t = b.evaluate(f, 500)
    y, _ = b.evaluate(f, 500)
    assert np.array_equal(x, y) and t == "500.000000" and x.dtype == np.int32
    same = renderer.render(genesis, "name", a, a, "standard")
    r = decoder.readout(b.evaluate(same, 500)[0], b.cells, 500)
    assert float(r["left_hz"]) > float(r["right_hz"]), "left bias must show when both sides are identical"
    mirrored = renderer.render(genesis, "name", c, a, "standard")
    z, _ = b.evaluate(mirrored, 500)
    assert not np.array_equal(x, z)
    blank = np.full((180, 320, 3), 128, np.uint8)
    assert decoder.readout(b.evaluate(blank, 500)[0], b.cells, 500)["gate_spikes"] == 0
