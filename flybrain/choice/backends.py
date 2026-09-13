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
    REWARD = np.arange(36, 51, dtype=np.int64)  # 15 "PAM11-like" stand-ins for game modes

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

    def atlas(self) -> dict:
        """Schematic cell positions for the dashboard. NOT anatomy: the fixture
        has no brain; positions only give the 64 cells a stable place inside a
        stylised fly-brain outline. Activity values shown on them are real."""
        pos = np.zeros((self.N, 3), dtype=np.float32)
        rng = np.random.default_rng(int.from_bytes(hashlib.sha256(b"flybrain-fixture-atlas").digest()[:8], "big"))
        for i in self.LEFT:
            pos[i] = [-0.28, -0.12, 0.18] + rng.normal(0, 0.05, 3)
        for i in self.RIGHT:
            pos[i] = [0.28, -0.12, 0.18] + rng.normal(0, 0.05, 3)
        for i in self.GATE:
            pos[i] = [0.0, -0.02, 0.24] + rng.normal(0, 0.03, 3)
        for i in self.OTHER:
            # scattered through the central brain and optic lobes
            region = rng.integers(0, 3)
            centre = [[0, 0.05, 0], [-0.82, 0, 0], [0.82, 0, 0]][region]
            radii = [[0.5, 0.36, 0.3], [0.26, 0.26, 0.22], [0.26, 0.26, 0.22]][region]
            pos[i] = np.asarray(centre) + rng.uniform(-1, 1, 3) * np.asarray(radii) * 0.8
        return {
            "model": FIXTURE_MODEL,
            "schematic": True,
            "note": "Fixture backend: positions are a schematic layout, not anatomy. Spike counts shown on them are the recorded values.",
            "n": int(self.N),
            "cells": {"left": self.LEFT.tolist(), "right": self.RIGHT.tolist(), "gate": self.GATE.tolist(), "reward": self.REWARD.tolist()},
            "positions": pos,
        }

    def observe(self, frame: np.ndarray, window_ms: int, reward: bool = False, learning: bool = True, pulse_ms: int = 200) -> dict:
        """Game-mode observation: same readout as evaluate(); a reward pulse adds
        spikes to the 15 stand-in reward cells. The fixture has no memory."""
        counts, neural_time = self.evaluate(frame, window_ms)
        if reward:
            counts = counts.copy()
            counts[self.REWARD] += int(round(30 * pulse_ms / 1000))
        return {"counts": counts, "neural_time_ms": neural_time, "reward_spikes": int(counts[self.REWARD].sum()), "kc_spikes": 0, "memory": {"changed_edges": 0, "plastic_edges": 0, "sha256": None}, "stimulus_ms": pulse_ms if reward else 0}

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

    def atlas(self) -> dict:
        """Soma positions for every retained neuron, from the MaleCNS annotations
        (normalised to the unit cube, NaN where the release has no soma)."""
        from ..neural.common import annotations

        n = self.brain.n
        pos = np.full((n, 3), np.nan, dtype=np.float32)
        try:
            a = annotations(self.brain.ids)
            col = next((c for c in ("somaLocation", "position", "soma_position") if c in a.columns), None)
            if col is not None:
                for i, v in enumerate(a[col].tolist()):
                    if v is None:
                        continue
                    if isinstance(v, str):
                        v = [float(x) for x in v.strip("[]() ").replace(",", " ").split()]
                    v = np.asarray(v, dtype=np.float64).ravel()
                    if v.shape == (3,) and np.isfinite(v).all():
                        pos[i] = v
            ok = np.isfinite(pos).all(axis=1)
            if ok.any():
                # Display-only orientation: principal axes, longest axis
                # vertical with the denser end (the brain, not the nerve
                # cord) up, and annotated left somata on the viewer's left.
                p = pos[ok].astype(np.float64)
                centre = p.mean(axis=0)
                p -= centre
                _, vecs = np.linalg.eigh(np.cov(p.T))
                axes = vecs[:, ::-1]  # columns: largest variance first
                q = p @ axes  # q[:,0] longest, q[:,1] second, q[:,2] shortest
                if np.median(q[:, 0]) < 0:
                    q[:, 0] *= -1
                sides = a["somaSide"].fillna("").to_numpy()[ok] if "somaSide" in a.columns else None
                if sides is not None and (sides == "L").any() and q[sides == "L", 1].mean() > 0:
                    q[:, 1] *= -1
                out = np.column_stack([q[:, 1], q[:, 0], q[:, 2]])  # x = width, y = long axis, z = depth
                out /= float(np.abs(out).max()) or 1.0
                pos[ok] = out.astype(np.float32)
        except Exception:  # positions are display-only; never block a run
            pos[:] = np.nan
        return {
            "model": CONNECTOME_MODEL,
            "schematic": False,
            "note": "MaleCNS v1.0 soma positions, normalised. Neurons without a released soma position are omitted from the view.",
            "n": int(n),
            "cells": {**{k: np.asarray(v).tolist() for k, v in self.cells.items()}, "reward": np.asarray(self.brain.circuit["reward"]).tolist()},
            "positions": pos,
        }

    def observe(self, frame: np.ndarray, window_ms: int, reward: bool = False, learning: bool = True, pulse_ms: int = 200, pulse_current: float = 20.0) -> dict:
        """Game-mode observation: the brain keeps its state between calls (no
        checkpoint restore), the candidate plasticity rule may run, and a hit
        delivers the Stonkfly reward pulse (an artificial current into the 15
        PAM11 dopamine cells for ``pulse_ms``). Engineered reinforcement, not
        pleasure. Returns the whole-window spike counts."""
        b = self.brain
        b.weights_frozen = not learning
        pulse_ms = min(int(pulse_ms), int(window_ms)) if reward else 0
        total = np.zeros(b.n, dtype=np.int32)
        if pulse_ms:
            c, _ = b.rgb_step(frame, float(pulse_ms), learning=learning, stimulation=(b.circuit["reward"], pulse_current))
            total += c
        if window_ms - pulse_ms > 0:
            c, _ = b.rgb_step(frame, float(window_ms - pulse_ms), learning=learning)
            total += c
        b.counts[:] = total
        mem = b.memory()
        return {
            "counts": total.astype(np.int32),
            "neural_time_ms": decimal_str(b.sim_ms),
            "reward_spikes": int(total[b.circuit["reward"]].sum()),
            "kc_spikes": int(total[b.circuit["kc"]].sum()),
            "memory": {"plastic_edges": int(mem["plastic_edges"]), "changed_edges": int(mem["changed_edges"]), "sha256": mem["sha256"], "mean_efficacy": decimal_str(mem["mean_efficacy"])},
            "stimulus_ms": pulse_ms,
        }

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
