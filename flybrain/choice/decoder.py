"""The fixed, published neural decoding rule. No other code may interpret spikes.

Readout cells (Stonkfly baseline): DNp20 left/right populations, DNpe017 gate.

Trial readout
    left_hz  = mean spike count over left cells  / window seconds
    right_hz = mean spike count over right cells / window seconds
    gate     = total spikes over gate cells

Attempt score (two mirrored trials, A and B are candidates)
    trial 1 shows A left,  B right:  a1 = left_hz - right_hz
    trial 2 shows B left,  A right:  a2 = right_hz - left_hz
    A_score = (a1 + a2) / 2,  B_score = -A_score
    A wins if A_score >= threshold; B wins if B_score >= threshold;
    otherwise INCONCLUSIVE. Either trial without a gate spike => NO_GATE.

A persistent left/right turning bias adds +b to a1 and -b to a2, so it cancels
in A_score. All arithmetic on recorded values uses Decimal on the exact
strings written to the envelopes, so a verifier reproduces it bit for bit.
"""

from decimal import ROUND_HALF_EVEN, Decimal

import numpy as np

from ..commitments.canonical import decimal_str

PLACES = Decimal("0.000001")


def readout(counts: np.ndarray, cells: dict, window_ms: int) -> dict:
    counts = np.asarray(counts)
    seconds = window_ms / 1000
    left = float(np.mean(counts[cells["left"]]) / seconds)
    right = float(np.mean(counts[cells["right"]]) / seconds)
    gate = int(counts[cells["gate"]].sum())
    return {
        "left_hz": decimal_str(left),
        "right_hz": decimal_str(right),
        "gate_spikes": gate,
        "raw_side": "NO_GATE" if not gate else "LEFT" if left > right else "RIGHT" if right > left else "TIE",
    }


def score(trial_1: dict, trial_2: dict, threshold: str) -> dict:
    """Candidate-relative score from two mirrored trial readouts."""
    if trial_1["gate_spikes"] < 1 or trial_2["gate_spikes"] < 1:
        return {"a_score": None, "b_score": None, "result": "NO_GATE"}
    a1 = Decimal(trial_1["left_hz"]) - Decimal(trial_1["right_hz"])
    a2 = Decimal(trial_2["right_hz"]) - Decimal(trial_2["left_hz"])
    a = ((a1 + a2) / 2).quantize(PLACES, rounding=ROUND_HALF_EVEN)
    b = -a
    thr = Decimal(threshold)
    result = "A" if a >= thr else "B" if b >= thr else "INCONCLUSIVE"
    return {"a_score": str(a), "b_score": str(b), "result": result}
