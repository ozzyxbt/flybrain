# FLYBRAIN

**A fly brain launched a coin.** Forget AI. We have flies now.

> The fly chose among a precommitted set of alternatives using a fixed, published neural decoding protocol. A pre-approved execution system submitted the resulting launch transaction.

FLYBRAIN shows a simulated fly connectome pairs of authored candidates (name, ticker, logo, palette, description, venue, launch/wait) and lets a fixed decoder over its DNp20/DNpe017 readout cells pick a winner in a mirrored, bias-resistant tournament. Every input frame, spike array, rate and decision is hash-chained; `flybrain verify-run` recomputes all of it. The neural core is the MIT-licensed [Stonkfly](https://github.com/nftechie/stonkfly) MaleCNS v1.0 model, retained byte-for-byte (166,700 neurons, 25.6 M edges, 0.1 ms C++ kernel). Not consciousness; profitable learning not demonstrated; see [docs/claims.md](docs/claims.md).

## Gate A (this release): deterministic local demo

```sh
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e '.[test]'
python -m pytest -q
flybrain run --manifest manifests/gate-a-demo-v1.json --out runs/demo --run-id gate-a-demo
flybrain verify-run runs/demo --resimulate
flybrain serve --run runs/demo            # http://127.0.0.1:8787/  (pixel-art replay), /choose, /coin, /brain
```

No wallet, network or dataset needed. Runs use the `fixture-brain-v1` backend (a deterministic stand-in, **not** the connectome) and the `mock` launch adapter (no real token). `LIVE_LAUNCH=false` / `NETWORK=mock` are the defaults and mainnet is unreachable from this build.

Two precommitted manifests ship: `manifests/genesis-v1.json` (six names; the fixture ended `NO_DECISION` on the name category, so `NO_LAUNCH`) and `manifests/gate-a-demo-v1.json` (four names; ended in a mock launch). Both outcomes are real outputs of the fixed protocol and are reported as such.

## Beer pong (game mode, `beer-pong` branch)

```sh
flybrain pong --out runs/pong-fixture                   # fixture backend
flybrain pong --backend malecns-connectome --checkpoint data/checkpoints/genesis.npz --out runs/pong-1
flybrain party --run runs/pong-1                        # http://127.0.0.1:8790/  (FLYPONG party app)
```

The fly throws where its DNp20 readout says (zeroed on an empty-table calibration), sinks cups, drinks on misses (each drink blurs and doubles the image the network sees), and receives the Stonkfly PAM11 reward pulse after a hit. Replayed in its own party-themed front end (3D table, disco lights, rotating brain hologram, dopamine meter), separate from the lab dashboard. Hash-chained; rules and the real/engineered/theatre split in [docs/beer-pong.md](docs/beer-pong.md). The committed fixture game is in `fixtures/games/pong-fixture`; a connectome game (3 hits / 9 throws, passed out) is attached to the release.

### flypong.xyz

The FLYPONG app is exported as a server-less static site (`site/`, deployed to GitHub Pages by `.github/workflows/pages.yml`, custom domain `flypong.xyz`):

```sh
flybrain export-party --run runs/pong-connectome --out site --cname flypong.xyz
```

The export bundles the page, three.js, the game's frames, spike arrays, atlas and chain, and a pre-built `api/index.json`; nothing runs on a server.

## Venues

Pump.fun: adapter gated until the official program/API review. pons: identified as an EVM launch protocol on Robinhood Chain (chain id 4663); `flybrain/launch/pons.py` builds and inspects the unsigned v2 `launchToken` call and never submits (`flybrain pons-preview`). Details and consequences in [docs/pons.md](docs/pons.md). Venue selection stays in simulation mode.

## Connectome backend

```sh
flybrain prepare        # ~1.1 GB MaleCNS download + graph compile, 16 GB RAM
flybrain verify-data
flybrain checkpoint --out data/checkpoints/genesis.npz   # prints the sha256 for the manifest
flybrain manifest-canonicalize my-draft.json manifests/my.json --checkpoint data/checkpoints/genesis.npz
FLYBRAIN_FULL_TEST=1 python -m pytest -q tests/test_neural.py
```

Set `"backend": "malecns-connectome"` in the draft. A full connectome run (`manifests/connectome-v1.json`, 44 trials, about 2 s of wall time per 500 ms trial on an M-series laptop) is reported in [docs/connectome-run.md](docs/connectome-run.md); its audit bundle is attached to the GitHub release rather than committed (35 MB of spike arrays).

## Layout

`flybrain/neural` retained core · `choice/` manifest, renderer, decoder, tournament, transcript, backends · `commitments/` canonical JSON, hash chain, memo payloads · `launch/` adapter interface, mock, gated placeholders · `risk/` veto-only guard · `verifier/` · `dashboard.py` + `web/` (`/` pixel-art replay of the chained run: the fly at its desk, the exact trial frame on its monitor, readout cells lit from the stored spike counts, LEFT/RIGHT presses per the recorded readout, coin reveal on launch; `/choose`, `/coin`, `/brain` data views) · `manifests/` · `docs/`.

## License

MIT. Attribution and dataset terms in [THIRD_PARTY.md](THIRD_PARTY.md).
