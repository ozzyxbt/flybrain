# Beer pong (game mode)

`flybrain pong` is a side game on the same retained connectome. It is **not** the choice protocol: the brain keeps its state between throws, the candidate plasticity rule may run, and an artificial reward current is delivered. Nothing here feeds into identity selection or launches.

```sh
flybrain pong --out runs/pong-fixture                                   # fixture backend, instant
flybrain pong --backend malecns-connectome --checkpoint data/checkpoints/genesis.npz --out runs/pong-1
flybrain party --run runs/pong-1       # http://127.0.0.1:8790/  (FLYPONG party app, separate front end)
```

## Rules (`flybrain/games/beerpong.py`)

| Rule | Value |
| --- | --- |
| cups | 6 in a triangle: lateral positions −0.5, 0, 0.5 (back row), −0.25, 0.25 (middle), 0 (front) |
| calibration | one observation of the empty table before the first throw, no reward; its right_hz − left_hz is the aim zero (`bias_hz`), chained |
| throw | one 500 ms observation of the rendered table; landing x = (right_hz − left_hz − bias_hz) / 6.0 Hz, clipped to [−1, 1] |
| hit | nearest remaining cup within radius 0.20 (front rows first); no DNpe017 spike = no throw registered |
| reward | on the throw **after** a hit: 20 mV-equivalent current into the 15 annotated PAM11 dopamine cells for 200 ms, plasticity rule enabled |
| miss | one drink; each drink blurs (box kernel 1 + 4·drinks px) and doubles (shift 4·drinks px, 40 %) the rendered frame the network sees from then on |
| end | table cleared, 12 throws, or 6 drinks ("passed out") |

Every throw records the exact frame, the whole-network spike array, DNp20/DNpe017 readout, landing point, hit/miss, PAM11 spikes and the plasticity summary, hash-chained like a choice run. The FLYPONG party app (`flybrain party`, its own front end and port; the lab dashboard has no game tab) replays the record: club-lit table, disco lights, confetti on hits, a rotating brain hologram beside the table, fly-cam shows what the network actually saw (including the drunk degradation), the CNS panel lights the cells that fired, PAM11 cells are marked in magenta and their rate is shown when the reward current was on.

## What is real and what is theatre

- Real: spike arrays, DNp20 rates, PAM11 spike counts, weight changes, the degraded input images.
- Engineered: the throw mapping (with the empty-table zeroing, the game analogue of the mirrored trials), the reward current (Stonkfly's existing PAM11 stimulation), the drink → image degradation rule.
- Theatre: wobbling, hiccups, drinking animation, passing out. The wobble amplitude is a display mapping of the drink count.
- Not shown or claimed: pleasure, intoxication, skill, learning. "Dopamine activity" is the firing rate of 15 identified cells under an artificial current, not dopamine concentration.
