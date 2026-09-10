"""Neural backends behind one interface: ``evaluate(frame, window_ms)``.

``ConnectomeBrain`` wraps the retained Stonkfly MaleCNS core (frozen weights,
restored from the published checkpoint before every trial).

``FixtureBrain`` is a small deterministic stand-in used for Gate A and the
test-suite. It is *not* a connectome and every artifact it produces says so.
It is content-responsive and carries a persistent side bias so the mirrored
protocol can be exercised end to end without the 1.1 GB dataset.
"""

import hashlib
import json
from pathlib import Path
from typing import Protocol

import numpy as np

from ..commitments.canonical import decimal_str, file_sha256

FIXTURE_MODEL = "fixture-brain-v1"
CONNECTOME_MODEL = "malecns-connectome"


class ChoiceBrain(Protocol):
    model: str
    checkpoint_sha256: str
    checkpoint_name: str
    cells: dict
    cell_ids: dict

    def evaluate(self, frame: np.ndarray, window_ms: int) -> tuple: ...


def _linear(frame_u8: np.ndarray) -> np.ndarray:
    x = frame_u8.astype(np.float64) / 255
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


class FixtureBrain:
    model = FIXTURE_MODEL
    N = 64
    LEFT = np.arange(0, 16, dtype=np.int64)
    RIGHT = np.arange(16, 32, dtype=np.int64)
    GATE = np.arange(32, 36, dtype=np.int64)
    OTHER = np.arange(36, 64, dtype=np.int64)

    def __init__(self, checkpoint_path):
        self.checkpoint_path = Path(checkpoint_path)
        self.checkpoint_name = self.checkpoint_path.name
        self.checkpoint_sha256 = file_sha256(self.checkpoint_path)
        p = json.loads(self.checkpoint_path.read_text())
        if p.get("model") != FIXTURE_MODEL:
            raise ValueError("Not a fixture-brain checkpoint")
        self.p = {
            k: float(p[k])
            for k in [
                "base_hz",
                "left_bias_hz",
                "luminance_gain_hz",
                "green_gain_hz",
                "edge_gain_hz",
                "taste_gain_hz",
                "gate_contrast_threshold",
                "jitter_hz",
            ]
        }
        self.cells = {"left": self.LEFT, "right": self.RIGHT, "gate": self.GATE}
        self.cell_ids = {
            "left": [f"fixture-L{i}" for i in range(16)],
            "right": [f"fixture-R{i}" for i in range(16)],
            "gate": [f"fixture-G{i}" for i in range(4)],
        }

    def _jitter(self, input_sha: str) -> np.ndarray:
        seed = hashlib.sha256((self.checkpoint_sha256 + input_sha).encode()).digest()
        out = np.empty(self.N, dtype=np.float64)
        for i in range(self.N):
            h = hashlib.sha256(seed + i.to_bytes(2, "big")).digest()
            out[i] = int.from_bytes(h[:8], "big") / 2**64  # [0, 1)
        return out

    # Card interiors (see renderer.LEFT_CARD / RIGHT_CARD, inside the border).
    # Both regions are the same size so a candidate's pixels are identical
    # whichever side it is shown on: the readout depends on content, not side,
    # apart from the explicit bias term.
    REGIONS = {"left": (10, 150, 30, 164), "right": (170, 310, 30, 164)}

    @staticmethod
    def features(frame: np.ndarray, x0: int, x1: int, y0: int = 0, y1: int = None) -> tuple:
        raw = frame[y0:y1, x0:x1, :]
        region = _linear(raw)
        lum = region @ np.asarray([0.2126, 0.7152, 0.0722])
        edge = float(np.mean(np.abs(np.diff(lum, axis=1))))
        # Idiosyncratic but deterministic "taste" for this exact content.
        taste = int.from_bytes(hashlib.sha256(np.ascontiguousarray(raw).tobytes()).digest()[:8], "big") / 2**64 * 2 - 1
        return float(lum.mean()), float(region[..., 1].mean()), edge, taste

    def evaluate(self, frame: np.ndarray, window_ms: int) -> tuple:
        frame = np.asarray(frame)
        if frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype != np.uint8:
            raise ValueError("RGB uint8 frame required")
        input_sha = hashlib.sha256(frame.tobytes()).hexdigest()
        u = self._jitter(input_sha)
        p = self.p
        seconds = window_ms / 1000
        rates = np.zeros(self.N, dtype=np.float64)
        for cells, side, sign in [(self.LEFT, "left", 1), (self.RIGHT, "right", -1)]:
            x0, x1, y0, y1 = self.REGIONS[side]
            lum, green, edge, taste = self.features(frame, x0, x1, y0, y1)
            pref = p["luminance_gain_hz"] * lum + p["green_gain_hz"] * green + p["edge_gain_hz"] * edge + p["taste_gain_hz"] * taste
            rates[cells] = p["base_hz"] + pref + sign * p["left_bias_hz"]
        rates += (u * 2 - 1) * p["jitter_hz"]
        full = _linear(frame) @ np.asarray([0.2126, 0.7152, 0.0722])
        contrast = float(full.std())
        counts = np.zeros(self.N, dtype=np.int32)
        counts[self.LEFT] = np.maximum(0, np.rint(rates[self.LEFT] * seconds)).astype(np.int32)
        counts[self.RIGHT] = np.maximum(0, np.rint(rates[self.RIGHT] * seconds)).astype(np.int32)
        if contrast > p["gate_contrast_threshold"]:
            counts[self.GATE] = 1 + (np.floor(u[self.GATE] * 3)).astype(np.int32)
        counts[self.OTHER] = np.floor(u[self.OTHER] * 6).astype(np.int32)
        return counts, decimal_str(window_ms)


class ConnectomeBrain:
    """Retained MaleCNS core, frozen. Requires the prepared dataset."""

    model = CONNECTOME_MODEL

    def __init__(self, checkpoint_path):
        from ..neural.common import annotations
        from ..neural.controller import Decoder
        from ..neural.visual import VisualMemoryBrain

        self.brain = VisualMemoryBrain()
        self.brain.weights_frozen = True
        decoder = Decoder(self.brain.ids, annotations(self.brain.ids), 1.0)
        self.cells = {"left": decoder.left, "right": decoder.right, "gate": decoder.gate}
        self.cell_ids = decoder.identities
        self.checkpoint_path = Path(checkpoint_path)
        self.checkpoint_name = self.checkpoint_path.name
        if not self.checkpoint_path.exists():
            # Genesis checkpoint: the untouched compiled graph at neural time 0.
            self.brain.checkpoint(self.checkpoint_path)
        self.brain.restore(self.checkpoint_path)
        self.checkpoint_sha256 = file_sha256(self.checkpoint_path)
        self.edges = self.brain.circuit["edges"]

    def evaluate(self, frame: np.ndarray, window_ms: int) -> tuple:
        b = self.brain
        b.restore(self.checkpoint_path)
        b.weights_frozen = True
        before = b.weight[self.edges].copy()
        counts, _ = b.rgb_step(frame, float(window_ms), learning=False)
        if not np.array_equal(before, b.weight[self.edges]):
            raise RuntimeError("Plastic weights changed during a frozen selection trial")
        return counts.astype(np.int32), decimal_str(b.sim_ms)


def open_backend(name: str, checkpoint_path) -> ChoiceBrain:
    if name == FIXTURE_MODEL:
        return FixtureBrain(checkpoint_path)
    if name == CONNECTOME_MODEL:
        return ConnectomeBrain(checkpoint_path)
    raise ValueError(f"Unknown backend {name}")
