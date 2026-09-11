# Connectome run: `connectome-v1`

Recorded 2026-09-11 on an Apple-silicon laptop (24 GB RAM, Python 3.11, Apple clang 17). Everything below is copied from real command output; the audit bundle is attached to the GitHub release as `flybrain-run-connectome-v1.zip` (SHA-256 `f464c38f6f77cb2d41012f4d767f8de529a83f87a7ca5a35d4b4e8dbdc7356f3`, 8.4 MB; 35 MB unpacked, mostly `spikes/*.npy`).

## Dataset

```
flybrain prepare
{"dataset": "malecns_v1", "neurons": 166700, "edges": 25582938, "synaptic_contacts": 124177617,
 "retina_total": 3377, "retina_mapped": 3335, "retina_unmapped": 42, ...}
{"release": "MaleCNS v1.0", "neurons": 166700, "directed_edges": 25582938, "arrays_verified": true}
```

Source files matched `flybrain/neural/sources.lock.json` (annotations 14,483,314 B; neurotransmitters 43,282,834 B; edges 1,051,241,946 B) and every compiled array matched `arrays.lock.json`.

## Baseline opt-in test

```
FLYBRAIN_FULL_TEST=1 python -m pytest -q tests/test_neural.py
3 passed in 4.68s
```

`test_full_connectome_frozen_selection_changes_no_weights`: 166,700 neurons, 25,582,938 edges, 3,335 R1–R6 and 811 R8 inputs; a 500 ms white-field trial produces spikes, the 7,835 plastic KC→MBON weights are unchanged afterwards, and a second trial from the restored checkpoint reproduces the identical spike array.

## Checkpoint and timing

```
brain ready in 3.2s; checkpoint a1e47261eba8cb2bd353646dd2ba048a214260e997f95c783429ebf9fae40078;
cells L=1 R=1 gate=2
trial 0: 2.1s wall, total spikes 519560, L=30.000000 R=38.000000 gate=14 raw=RIGHT sha=c8621a75a5cf7cec
trial 1: 2.1s wall, total spikes 519560, L=30.000000 R=38.000000 gate=14 raw=RIGHT sha=c8621a75a5cf7cec
atlas positions ok: 139662 / 166700
```

MaleCNS v1.0 annotates one DNp20 per side and two DNpe017 cells, so at a 500 ms window the readout rates are multiples of 2 Hz. 139,662 neurons have a released `somaLocation`; the rest are omitted from the brain view.

## Tournament

Manifest `manifests/connectome-v1.json`, SHA-256 `975e1b1bacc2674d72f97140955879b9d8d908250eb60a7ea988718bf5be941e` (same candidates as `gate-a-demo-v1`, backend `malecns-connectome`). 44 trials, 72 chain entries.

| Category | Result | Attempts used |
| --- | --- | --- |
| name | PROBOSCIS | 1, 1, 2 |
| ticker | FLY | 1, 1, 1 |
| logo | SPIKE | 1, 1, 1 |
| palette | AMBER GLOW | 1, 1, 1 |
| description | FORGET AI. WE HAVE FLIES NOW. | 2, 3, 1 |
| launch venue | pumpfun (simulation mode) | 1 |
| launch action | LAUNCH, window 1 | 2 |

Raw trial readouts leaned RIGHT far more often than LEFT (a persistent readout bias of the frozen network under these inputs). The mirrored score is what decided each match; for example `name r2 m1` attempt 1 read RIGHT in both orientations (a1 = −4, a2 = +2 → A_score −1, inconclusive) and only attempt 2 (`high_contrast`) separated the candidates. `description r1 m2` needed all three attempts.

Final decision `58eb08dafdc84422a98dc1143683bf30bfb1d57244a6aa9429440e0c600938e3`; mock launch intent `809cb4feff026810…`; receipt `387986a99f446b0e11d47b820f1701350faf26e5338ac2c286422f9cbfe3b4c5`; simulated mint `5aEMTipVgSeLfhS2oLEBSu8SjYuSoSqshfKjHv6SVL21` (network `mock`, not a token).

```
flybrain verify-run runs/connectome-v1
OK: 837 checks, 0 failures, 0 warnings
```

The verifier re-rendered all 44 frames from the manifest, recomputed the DNp20/DNpe017 rates from the stored spike arrays using the atlas cell indices bound to the run header, recomputed every mirrored score, the bracket, the launch windows, the final decision and the mock receipt.

## What this shows and does not show

- The full retained MaleCNS graph, unchanged from the Stonkfly baseline, drives the fixed decoder end to end on this protocol, deterministically and fast enough for live use (about 2 s of wall time per 500 ms of neural time).
- A launch is possible from real connectome output, and so is `NO_DECISION`: the protocol does not guarantee either.
- It does not show preference, understanding or intent. The readout is an engineered mapping of two DNp20 cells and two DNpe017 cells; a rightward bias under white cards is a property of the model plus display adapter, not a judgement about the candidates. See `docs/claims.md`.
