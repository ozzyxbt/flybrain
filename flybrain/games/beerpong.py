"""Beer pong for a fly connectome. A game mode, not the choice protocol.

Every throw is one 500 ms observation of the table (the fly's view is a
rendered RGB frame of the remaining cups). The fixed DNp20 readout aims the
ball: lateral landing position = (right_hz − left_hz − bias_hz) / aim_scale_hz,
where bias_hz is the readout's right-minus-left rate on an empty table,
measured once at the start (recorded, chained). A ball that lands within a
cup's radius sinks it.

Hit  → the next observation carries the Stonkfly reward pulse: a 20 mV-eq.
       current into the 15 annotated PAM11 dopamine cells for 200 ms, with the
       candidate plasticity rule enabled. Engineered reinforcement; reported as
       measured PAM11 spikes. Not pleasure.
Miss → the fly "drinks": each drink degrades its *visual input* (box blur and
       a horizontal double image on the rendered frame), so later throws are
       made from a worse picture. No neural parameter is changed; drunkenness
       is a documented input transform plus display animation.

Everything is hash-chained like a choice run so the game record can be
replayed and audited (`chain.jsonl`, frames, spike arrays).
"""

import hashlib
import json
import time
from decimal import Decimal
from pathlib import Path

import numpy as np

from .. import software
from ..choice import decoder, font
from ..choice.backends import open_backend
from ..choice.renderer import save_png
from ..commitments.canonical import decimal_str, file_sha256, write_canonical
from ..commitments.hashchain import HashChain

PROTOCOL = "fly-pong-v1"
RULES = {
    "cups": [["-0.5", 2], ["0", 2], ["0.5", 2], ["-0.25", 1], ["0.25", 1], ["0", 0]],  # (lateral x as decimal string in [-1,1], row from the fly: 0 nearest)
    "cup_radius": "0.20",
    "max_throws": 12,
    "window_ms": 500,
    "aim_scale_hz": "6.0",
    "reward_pulse_ms": 200,
    "learning": True,
    "drink_blur_px": 2,
    "drink_shift_px": 4,
    "max_drinks": 6,
}
WIDTH, HEIGHT = 320, 180


def render_table(remaining: list, drinks: int) -> np.ndarray:
    """The fly's view: a green table receding to the far edge with red cups."""
    frame = np.empty((HEIGHT, WIDTH, 3), dtype=np.uint8)
    frame[:] = (235, 240, 249)
    frame[100:, :] = (34, 110, 70)  # table top
    frame[96:100, :] = (240, 240, 240)  # far edge line
    for x, row in remaining:
        depth = 1 - row / 2  # 1 = near (row 0), 0 = far
        cx = int(WIDTH / 2 + float(x) * (70 + 70 * depth))
        w = int(10 + 10 * depth)
        h = int(18 + 16 * depth)
        top = int(100 + 8 + (1 - depth) * 4 + depth * 40)
        frame[top : top + h, max(0, cx - w) : min(WIDTH, cx + w)] = (185, 28, 28)
        frame[top : top + 3, max(0, cx - w) : min(WIDTH, cx + w)] = (255, 255, 255)
    font.draw_text(frame, 8, 6, "BEER PONG", (19, 36, 71), 2)
    font.draw_text(frame, 8, 26, f"CUPS {len(remaining)} DRINKS {drinks}", (19, 36, 71), 1)
    return drunk_filter(frame, drinks)


def drunk_filter(frame: np.ndarray, drinks: int) -> np.ndarray:
    """Documented input degradation: box blur + double image, growing per drink."""
    if drinks <= 0:
        return frame
    k = 1 + 2 * drinks * RULES["drink_blur_px"]
    f = frame.astype(np.float32)
    pad = k // 2
    padded = np.pad(f, ((pad, pad), (pad, pad), (0, 0)), mode="edge")
    cs = np.cumsum(np.cumsum(padded, axis=0), axis=1)
    cs = np.pad(cs, ((1, 0), (1, 0), (0, 0)))
    blurred = (cs[k:, k:] - cs[:-k, k:] - cs[k:, :-k] + cs[:-k, :-k]) / (k * k)
    shift = drinks * RULES["drink_shift_px"]
    double = np.roll(blurred, shift, axis=1)
    out = 0.6 * blurred + 0.4 * double
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def landing(left_hz: str, right_hz: str, bias_hz: str = "0") -> str:
    """Lateral landing position. ``bias_hz`` is the readout's own right-minus-
    left rate on an empty table, measured once at the start of the game and
    recorded, so a persistent turning bias does not aim every throw off the
    table (the game-mode analogue of the choice protocol's mirrored trials)."""
    x = (Decimal(right_hz) - Decimal(left_hz) - Decimal(bias_hz)) / Decimal(RULES["aim_scale_hz"])
    x = max(Decimal(-1), min(Decimal(1), x))
    return str(x.quantize(Decimal("0.000001")))


def hit_test(land_x: str, remaining: list):
    """Nearest remaining cup (front rows first) within cup_radius, else None."""
    lx = Decimal(land_x)
    best = None
    for x, row in sorted(remaining, key=lambda c: (c[1], abs(Decimal(str(c[0])) - lx))):
        d = abs(Decimal(str(x)) - lx)
        if d <= Decimal(RULES["cup_radius"]):
            best = [x, row]
            break
    return best


def play(backend: str, checkpoint_path, out_dir, run_id=None, throws=None, log=print) -> dict:
    brain = open_backend(backend, checkpoint_path)
    out = Path(out_dir)
    if (out / "chain.jsonl").exists():
        raise RuntimeError(f"{out} already holds a game; use a fresh directory")
    for d in ["frames", "spikes", "throws", "brain"]:
        (out / d).mkdir(parents=True, exist_ok=True)
    run_id = run_id or f"pong-{int(time.time())}"
    rules = {**RULES, "max_throws": int(throws or RULES["max_throws"])}
    atlas = brain.atlas()
    positions = np.ascontiguousarray(atlas.pop("positions"), dtype="<f4")
    (out / "brain" / "positions.f32").write_bytes(positions.tobytes())
    atlas["positions_path"] = "brain/positions.f32"
    atlas["positions_sha256"] = hashlib.sha256(positions.tobytes()).hexdigest()
    write_canonical(out / "brain" / "atlas.json", atlas)
    chain = HashChain(out)
    chain.append("pong_header", "run.json", {
        "protocol": PROTOCOL, "run_id": run_id, "backend": brain.model, "checkpoint_sha256": brain.checkpoint_sha256,
        "rules": rules, "decoder_cells": brain.cell_ids, "reward_cells": len(atlas["cells"]["reward"]),
        "atlas": {"path": "brain/atlas.json", "sha256": file_sha256(out / "brain" / "atlas.json"), "schematic": atlas["schematic"]},
        "software": software.identity(), "learning": rules["learning"],
        "disclosure": "Throws are decoded from DNp20 left/right activity by a fixed rule. Hits deliver an artificial current to PAM11 dopamine cells (engineered reinforcement, not pleasure). Misses degrade the rendered visual input (blur, double image); no neural parameter changes. A game, not evidence of skill, learning or experience.",
    })
    # Calibration: one observation of the empty table, no reward. Its
    # right-minus-left rate becomes the aim zero for the whole game.
    cal_frame = render_table([], 0)
    cal = brain.observe(cal_frame, rules["window_ms"], reward=False, learning=rules["learning"])
    cal_counts = np.ascontiguousarray(cal["counts"], dtype="<i4")
    save_png(cal_frame, out / "frames" / "calibration.png")
    np.save(out / "spikes" / "calibration.npy", cal_counts)
    cal_read = decoder.readout(cal_counts, brain.cells, rules["window_ms"])
    bias_hz = str((Decimal(cal_read["right_hz"]) - Decimal(cal_read["left_hz"])).quantize(Decimal("0.000001")))
    chain.append("calibration", "throws/calibration.json", {
        "protocol": PROTOCOL, "run_id": run_id, "input_sha256": hashlib.sha256(cal_frame.tobytes()).hexdigest(), "spike_sha256": hashlib.sha256(cal_counts.tobytes()).hexdigest(),
        "frame_path": "frames/calibration.png", "spike_path": "spikes/calibration.npy", "left_hz": cal_read["left_hz"], "right_hz": cal_read["right_hz"], "gate_spikes": cal_read["gate_spikes"],
        "bias_hz": bias_hz, "note": "Empty table, no reward. right_hz - left_hz on this frame is subtracted from every throw's aim.",
    })
    log(f"calibration: L={cal_read['left_hz']} R={cal_read['right_hz']} -> aim zero (bias) {bias_hz} Hz")
    remaining = [list(c) for c in rules["cups"]]
    drinks = 0
    hits = 0
    pending_reward = False
    records = []
    for n in range(1, rules["max_throws"] + 1):
        if not remaining or drinks >= rules["max_drinks"]:
            break
        frame = render_table(remaining, drinks)
        obs = brain.observe(frame, rules["window_ms"], reward=pending_reward, learning=rules["learning"], pulse_ms=rules["reward_pulse_ms"])
        counts = np.ascontiguousarray(obs["counts"], dtype="<i4")
        key = f"throw-{n:02d}"
        save_png(frame, out / "frames" / f"{key}.png")
        np.save(out / "spikes" / f"{key}.npy", counts)
        read = decoder.readout(counts, brain.cells, rules["window_ms"])
        land = landing(read["left_hz"], read["right_hz"], bias_hz)
        cup = hit_test(land, remaining) if read["gate_spikes"] > 0 else None
        hit = cup is not None
        drinks_before = drinks
        if hit:
            remaining.remove(cup)
            hits += 1
        else:
            drinks += 1
        env = {
            "protocol": PROTOCOL, "run_id": run_id, "throw": n,
            "cups_before": [list(c) for c in (remaining + [cup] if hit else remaining)], "drinks_before": drinks_before,
            "input_sha256": hashlib.sha256(frame.tobytes()).hexdigest(), "spike_sha256": hashlib.sha256(counts.tobytes()).hexdigest(),
            "frame_path": f"frames/{key}.png", "spike_path": f"spikes/{key}.npy",
            "left_hz": read["left_hz"], "right_hz": read["right_hz"], "gate_spikes": read["gate_spikes"],
            "bias_hz": bias_hz, "landing_x": land, "hit": hit, "cup": cup, "cups_after": [list(c) for c in remaining], "drinks_after": drinks,
            "reward_applied_ms": obs["stimulus_ms"], "reward_spikes": obs["reward_spikes"], "reward_hz": decimal_str(obs["reward_spikes"] / max(1, len(atlas["cells"]["reward"])) / (rules["window_ms"] / 1000)),
            "kc_spikes": obs["kc_spikes"], "memory": obs["memory"], "neural_time_ms": obs["neural_time_ms"], "backend": brain.model,
        }
        chain.append("throw", f"throws/{key}.json", env)
        records.append(env)
        pending_reward = hit
        log(f"throw {n:02d}: L={read['left_hz']} R={read['right_hz']} gate={read['gate_spikes']} land={land} -> {'HIT ' + str(cup) if hit else 'miss'} · drinks {drinks} · PAM11 {obs['reward_spikes']} spikes · plastic edges changed {obs['memory']['changed_edges']}")
    result = "TABLE CLEARED" if not remaining else ("PASSED OUT" if drinks >= rules["max_drinks"] else "OUT OF THROWS")
    final = {"protocol": PROTOCOL, "run_id": run_id, "throws": len(records), "hits": hits, "misses": len(records) - hits, "drinks": drinks, "cups_left": len(remaining), "result": result}
    chain.append("pong_result", "result.json", final)
    summary = {**final, "backend": brain.model, "chain_head": chain.head, "chain_length": chain.seq}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    log(f"result: {result} · {hits} hits / {len(records)} throws · {drinks} drinks")
    return summary
