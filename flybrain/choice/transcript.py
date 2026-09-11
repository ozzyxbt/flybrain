"""Run directory layout and the durable, hash-chained transcript.

    <run>/
      manifest.json         canonical bytes of the precommitted manifest
      checkpoint/<file>     the frozen brain checkpoint the manifest names
      run.json              chain seq 0: run header (backend, software, cells)
      frames/<key>.png      exact RGB input of every trial
      spikes/<key>.npy      int32 spike counts of every trial
      trials/<key>.json     decision envelope per trial (chained)
      matches/...json       mirrored-attempt scores per match (chained)
      categories/...json    bracket and winner per category (chained)
      final/decision.json   composed identity + launch decision (chained)
      launch/...json        intent before submission, receipt after (chained)
      chain.jsonl           index of the chain
      commitments.jsonl     memo payloads that a committer would publish
"""

import hashlib
import shutil
import time
from pathlib import Path

import numpy as np

from .. import PROTOCOL
from ..commitments.canonical import file_sha256, write_canonical
from ..commitments.hashchain import HashChain
from ..commitments.solana_memo import LocalCommitter
from . import renderer


class Transcript:
    def __init__(self, root, manifest, manifest_sha256, brain, run_id, software, committer=None):
        self.root = Path(root)
        self.manifest = manifest
        self.manifest_sha256 = manifest_sha256
        self.run_id = run_id
        self.root.mkdir(parents=True, exist_ok=True)
        for d in ["checkpoint", "frames", "spikes", "trials", "matches", "categories", "final", "launch"]:
            (self.root / d).mkdir(exist_ok=True)
        if (self.root / "chain.jsonl").exists():
            raise RuntimeError(f"{self.root} already holds a run; use a fresh directory")
        digest = write_canonical(self.root / "manifest.json", manifest)
        if digest != manifest_sha256:
            raise RuntimeError("Manifest bytes changed between load and transcript")
        (self.root / "manifest.sha256").write_text(digest + "\n")
        target = self.root / "checkpoint" / brain.checkpoint_name
        shutil.copyfile(brain.checkpoint_path, target)
        if file_sha256(target) != manifest["brain_checkpoint_sha256"]:
            raise RuntimeError("Backend checkpoint does not match the manifest's brain_checkpoint_sha256")
        self.chain = HashChain(self.root)
        self.committer = committer or LocalCommitter(self.root, run_id)
        atlas_info = None
        if hasattr(brain, "atlas"):
            atlas = brain.atlas()
            (self.root / "brain").mkdir(exist_ok=True)
            positions = np.ascontiguousarray(atlas.pop("positions"), dtype="<f4")
            (self.root / "brain" / "positions.f32").write_bytes(positions.tobytes())
            atlas["positions_path"] = "brain/positions.f32"
            atlas["positions_sha256"] = hashlib.sha256(positions.tobytes()).hexdigest()
            write_canonical(self.root / "brain" / "atlas.json", atlas)
            atlas_info = {"path": "brain/atlas.json", "sha256": file_sha256(self.root / "brain" / "atlas.json"), "schematic": atlas["schematic"]}
        self.chain.append(
            "run_header",
            "run.json",
            {
                "protocol": PROTOCOL,
                "run_id": run_id,
                "manifest_sha256": manifest_sha256,
                "manifest_id": manifest["manifest_id"],
                "backend": brain.model,
                "checkpoint_file": brain.checkpoint_name,
                "checkpoint_sha256": brain.checkpoint_sha256,
                "decoder_cells": brain.cell_ids,
                "atlas": atlas_info,
                "software": software,
                "learning_frozen": True,
                "reinforcement_injected": False,
                "llm_in_decision_path": False,
            },
        )
        self.committer.commit("manifest", manifest_sha256)
        # Wall-clock metadata lives outside the chain so identical protocol
        # inputs yield identical envelope hashes across reruns.
        (self.root / "run-meta.json").write_text(
            '{"started_unix": %d, "run_id": "%s"}\n' % (int(time.time()), run_id)
        )

    def add(self, kind: str, relative_path: str, artifact: dict) -> str:
        return self.chain.append(kind, relative_path, artifact)

    def save_trial_inputs(self, key: str, frame: np.ndarray, counts: np.ndarray) -> dict:
        frame = np.ascontiguousarray(frame, dtype=np.uint8)
        counts = np.ascontiguousarray(counts, dtype="<i4")
        frame_path = self.root / "frames" / f"{key}.png"
        spike_path = self.root / "spikes" / f"{key}.npy"
        renderer.save_png(frame, frame_path)
        np.save(spike_path, counts)
        return {
            "input_sha256": hashlib.sha256(frame.tobytes()).hexdigest(),
            "spike_sha256": hashlib.sha256(counts.tobytes()).hexdigest(),
            "frame_path": f"frames/{key}.png",
            "spike_path": f"spikes/{key}.npy",
        }


def spike_sha256(counts: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(counts, dtype="<i4").tobytes()).hexdigest()


def frame_sha256(frame: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(frame, dtype=np.uint8).tobytes()).hexdigest()
