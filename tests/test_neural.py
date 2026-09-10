"""Stonkfly baseline unit tests carried over, plus the opt-in full-connectome
frozen-selection test."""

import os

import numpy as np
import pandas as pd
import pytest

from flybrain.neural.controller import Decoder
from flybrain.neural.rule import advance


def test_fixed_neuron_decoder():
    a = pd.DataFrame({"type": ["DNp20", "DNp20", "DNpe017"], "somaSide": ["L", "R", "L"]})
    d = Decoder(np.array([1, 2, 3]), a, 2)
    assert d.decode(np.array([0, 10, 0]), 0.5)["side"] == "HOLD"
    assert d.decode(np.array([0, 10, 1]), 0.5)["side"] == "BUY"
    assert d.decode(np.array([10, 0, 1]), 0.5)["side"] == "SELL"
    assert d.decode(np.array([4, 4, 1]), 0.5)["side"] == "HOLD"


def trace_protocol(order, frozen=False):
    k = np.zeros(2)
    d = np.zeros(1)
    u = np.zeros(2)
    w = np.zeros(2)
    gain = np.ones((1, 2))
    for phase in order:
        for _ in range(20):
            kh = np.array([20.0, 0.0]) if phase == "cue" else np.zeros(2)
            dh = np.array([30.0]) if phase == "reinforce" else np.zeros(1)
            advance(k, d, u, w, kh, dh, gain, 0.01, 0.001, frozen=frozen)
    return w


def test_memory_rule_temporal_specificity():
    paired = trace_protocol(["cue", "reinforce"])
    reverse = trace_protocol(["reinforce", "cue"])
    assert paired[0] < 0 and reverse[0] > 0
    assert paired[1] == 0 and reverse[1] == 0
    assert np.array_equal(trace_protocol(["cue", "reinforce"], True), np.zeros(2))


@pytest.mark.skipif(os.environ.get("FLYBRAIN_FULL_TEST") != "1", reason="Needs the prepared 1.1 GB MaleCNS dataset; explicit integration test")
def test_full_connectome_frozen_selection_changes_no_weights(tmp_path):
    from flybrain.choice.backends import ConnectomeBrain
    from flybrain.neural.data import verify

    assert verify()["neurons"] == 166700
    b = ConnectomeBrain(tmp_path / "genesis.npz")
    assert len(b.brain.post) == 25582938 and len(b.brain.retina) == 3335 and len(b.brain.r8) == 811
    white = np.full((180, 320, 3), 255, np.uint8)
    before = b.brain.weight[b.edges].copy()
    counts, t = b.evaluate(white, 500)
    assert counts.sum() > 0 and t == "500.000000"
    assert np.array_equal(before, b.brain.weight[b.edges])
    again, _ = b.evaluate(white, 500)
    assert np.array_equal(counts, again), "restoring the checkpoint must make trials reproducible"
