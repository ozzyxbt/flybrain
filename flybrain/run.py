"""Orchestrate one complete Gate A run: manifest -> tournament -> launch -> summary."""

import hashlib
import json
import time
from pathlib import Path

from . import software
from .choice import manifest as manifest_module
from .choice import renderer
from .choice.backends import open_backend
from .choice.tournament import Tournament
from .choice.transcript import Transcript
from .launch.base import build_intent
from .launch.mock import MockLaunchAdapter, MockSigner
from .launch.pipeline import LaunchHalted, execute_launch
from .risk.policy import LaunchGuard, LaunchSettings, Veto


def logo_png_sha256(manifest, logo_id: str, out_path: Path) -> str:
    """Render the chosen logo alone (8x8 sprite at 16px cells) for metadata."""
    import numpy as np

    c = manifest_module.candidate(manifest, "logo", logo_id)
    cell = 16
    img = np.empty((8 * cell, 8 * cell, 3), dtype=np.uint8)
    img[:] = renderer.hex_rgb(c["bg"])
    fg = np.asarray(renderer.hex_rgb(c["fg"]), dtype=np.uint8)
    for r, row in enumerate(c["pixels"]):
        for k, bit in enumerate(row):
            if bit == "#":
                img[r * cell : (r + 1) * cell, k * cell : (k + 1) * cell] = fg
    renderer.save_png(img, out_path)
    return hashlib.sha256(img.tobytes()).hexdigest()


def run(manifest_path, checkpoint_path, out_dir, run_id=None, settings=None, adapter=None, signer=None, log=print):
    manifest, msha = manifest_module.load(manifest_path)
    brain = open_backend(manifest["backend"], checkpoint_path)
    if brain.checkpoint_sha256 != manifest["brain_checkpoint_sha256"]:
        raise RuntimeError(
            f"Checkpoint {brain.checkpoint_sha256[:16]} does not match manifest brain_checkpoint_sha256 {manifest['brain_checkpoint_sha256'][:16]}"
        )
    run_id = run_id or f"{manifest['manifest_id']}-{int(time.time())}"
    out = Path(out_dir)
    t = Transcript(out, manifest, msha, brain, run_id, software.identity())
    log(f"run {run_id}: manifest {msha[:16]} checkpoint {brain.checkpoint_sha256[:16]} backend {brain.model}")
    final, final_sha = Tournament(manifest, msha, brain, t, log).run()
    settings = settings or LaunchSettings.from_env()
    adapter = adapter or MockLaunchAdapter(out / "launch" / "mock-ledger")
    signer = signer or MockSigner()
    guard = LaunchGuard(settings, adapter.program_ids)
    launch_status = {"status": "NOT_ATTEMPTED", "reason": final["reason"]}
    if final["outcome"] == "LAUNCH":
        sha = logo_png_sha256(manifest, final["identity"]["logo"], out / "final" / "logo.png")
        intent = build_intent(final, final_sha, manifest, run_id, settings, sha)
        try:
            receipt, rsha = execute_launch(t, intent, final, final_sha, adapter, signer, guard, log)
            launch_status = {"status": receipt["status"], "mint": receipt["receipt"]["mint"], "receipt_sha256": rsha}
        except Veto as e:
            t.add("launch_veto", "launch/veto.json", {"protocol": "fly-choice-v1", "run_id": run_id, "final_decision_sha256": final_sha, "veto": str(e)})
            launch_status = {"status": "VETOED", "reason": str(e)}
            log(f"launch vetoed: {e}")
        except LaunchHalted as e:
            launch_status = {"status": "HALTED", "reason": str(e)}
            log(f"launch halted: {e}")
    summary = {
        "run_id": run_id,
        "manifest_sha256": msha,
        "checkpoint_sha256": brain.checkpoint_sha256,
        "backend": brain.model,
        "final_decision_sha256": final_sha,
        "identity": final["identity"],
        "launch_venue": final["launch_venue"],
        "launch_action": final["launch_action"],
        "outcome": final["outcome"],
        "launch": launch_status,
        "chain_head": t.chain.head,
        "chain_length": t.chain.seq,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary
