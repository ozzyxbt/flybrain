# FLYBRAIN

- The neural core in `flybrain/neural/` is the Stonkfly baseline (commit `78ef3e0`). Keep it byte-identical; `tests/test_baseline_integrity.py` enforces it. Only `common.py` (data path env var) and `data.py` (package path) differ, and both differences are recorded in `flybrain/neural/BASELINE.json`.
- Layers stay separate: manifest → renderer → neural backend → fixed decoder → chained transcript → veto-only guard → launch adapter → receipt/dashboard. Nothing may sit between the decoder and the recorded choice: no LLM, no price logic, no operator override, no post-hoc selection, no rerun-until-favourable.
- Every committed artifact is canonical JSON with **no floats**; measured quantities are decimal strings. Use `flybrain.commitments.canonical`. Anything hashed must be reproducible from the manifest and stored inputs.
- Identity selection runs with plasticity frozen and no reinforcement. `WAIT`, `NO_DECISION`, vetoes, halts and failed launches are recorded and shown, never hidden or replaced.
- Development defaults: `LIVE_LAUNCH=false`, `NETWORK=mock`. Mainnet is not reachable from this build. No seed phrases or keys in source, examples, logs, prompts or artifacts.
- Public wording: the fly **selected among precommitted, authored candidates** using a fixed published decoder. Do not claim it invented language, understood money, formed intentions or is conscious; do not claim profitable learning or returns.
- Keep README short; details go in `docs/`.
