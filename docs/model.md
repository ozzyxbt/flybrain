# The model behind a choice

## Retained neural core

FLYBRAIN uses the Stonkfly neural core unchanged (`flybrain/neural/`, baseline commit `78ef3e0`; integrity enforced by `tests/test_baseline_integrity.py`). In brief:

- **MaleCNS v1.0** retained graph: 166,700 neurons, 25,582,938 directed edges, 124,177,617 synaptic contacts. Import verifies the released files against SHA-256 locks and every compiled array against `arrays.lock.json`.
- **Kernel**: C++17 event-driven leaky integrate-and-fire at 0.1 ms, 20 ms membrane / 5 ms synaptic constants, −45 mV threshold, 1.8 ms delay, 2.2 ms refractory. Contact count × 0.275 sets initial magnitude; ACh excitatory, GABA/glutamate/histamine inhibitory, positive fallback for unresolved signs. A coarse proxy, not receptor physiology.
- **Vision**: a 320×180 RGB frame drives 3,335 mapped R1–R6 cells (linear-sRGB luminance) and 811 mapped R8 cells (blue/green proxies) at inferred retinal positions. A display adapter, not validated fly vision.
- **Plasticity**: a candidate KC→MBON07/MBON11 rule exists in the core. For identity selection it is **frozen** (`weights_frozen=True`, `learning=False`), and `ConnectomeBrain.evaluate` raises if any plastic weight changes during a trial. No reinforcement is injected.

Full notes on assumptions and evidence: the baseline's [docs/model.md](https://github.com/nftechie/stonkfly/blob/78ef3e05ab0fa086032098558d893667068944a0/docs/model.md).

## Choice frame

`flybrain/choice/renderer.py` draws two 144×138 cards on a 320×180 frame with a symmetric header. Text uses a fixed 5×7 bitmap font (no system fonts) so a frame is byte-identical everywhere. Category-specific layouts: ticker at up to 4× scale, name 3×, description wrapped 1×, logos as 8×8 sprites at 12 px cells, palettes as horizontal bands. Three predeclared presentation variants (`standard`, `high_contrast`, `large`) are the only thing that differs between attempts of a match.

## Decoder (fixed, published)

Readout cells are the baseline's DNp20 left/right populations and the DNpe017 gate. For a match A vs B:

```
trial 1: A left, B right   a1 = left_hz − right_hz
trial 2: B left, A right   a2 = right_hz − left_hz
A_score = (a1 + a2) / 2    B_score = −A_score
A wins if A_score ≥ threshold; B wins if B_score ≥ threshold; else INCONCLUSIVE.
Either trial without a DNpe017 spike ⇒ NO_GATE (inconclusive).
```

A persistent left/right bias `b` adds `+b` to `a1` and `−b` to `a2` and cancels. Arithmetic runs on the exact decimal strings in the envelopes (`Decimal`), so a verifier reproduces it bit for bit. Threshold: 2.0 Hz. Window: 500 ms of neural time from the frozen checkpoint, restored before every trial.

## Fixture backend

`fixture-brain-v1` is a 64-cell deterministic stand-in used by Gate A and the tests: content-responsive (luminance, green, edge density, and a hash-derived “taste” of each card interior), a persistent +1.5 Hz left bias, hash-seeded jitter, and a contrast-gated DNpe017 stand-in. Its parameters live in `manifests/fixture-checkpoint-v1.json`, whose hash the manifest commits to. It is **not a connectome** and carries no biological meaning; it exists so the protocol, chain, verifier and dashboard can be exercised without the 1.1 GB dataset.

## Not demonstrated

Learning, profitable behavior, biological realism of the visual pathway, or any correspondence between simulated DNp20 activity and a fly's preferences. See `docs/claims.md`.
