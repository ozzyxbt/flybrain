# Verifying a run

```sh
flybrain verify-run runs/demo              # structure, hashes, rules
flybrain verify-run runs/demo --resimulate # fixture backend: rerun the model too
flybrain verify-run runs/demo --json       # machine-readable report
```

Exit status is nonzero on any failure. The report lists every check.

## What is recomputed

| Link | Check |
| --- | --- |
| manifest | canonical bytes re-encode identically; validator passes; hash equals `manifest.sha256` and `run.json` |
| checkpoint | `checkpoint/<file>` hashes to `brain_checkpoint_sha256` |
| chain | `chain.jsonl` sequence is contiguous; every artifact's bytes hash to its entry; every `previous_sha256` links to the prior artifact |
| trial | candidates exist and differ; variant is the predeclared one for that attempt; PNG pixels hash to `input_sha256`; **the frame re-renders identically from the manifest**; spike `.npy` hashes to `spike_sha256`; left/right rates and gate recomputed from spikes equal the envelope; (`--resimulate`) fixture output equals stored spikes |
| match | both trials in chain, mirrored, same category/round/match; readouts copied faithfully; score and result recomputed with the fixed rule; no attempt after a decision; `NO_DECISION` only after every predeclared attempt |
| category | pairing follows manifest order; byes as predicted; stopped at the first `NO_DECISION`; winner recomputed from the bracket |
| launch windows | at most `max_windows`; header `WINDOW i/n`; `launch` ends the sequence; `wait`/`NO_DECISION` schedule the published interval; no window after a launch |
| final | identity and roots equal category winners/hashes; outcome consistent; venue/launch skipped when identity incomplete; final artifact after every category |
| launch | at most one intent and receipt; intent hash and references; intent identity equals the manifest text of the winners; not mainnet; no dev buy or insider wallets; logo hash; mock mint/signature recomputed from the intent hash; receipt after intent; receipt metadata equals identity; authorities revoked |
| commitments | `commitments.jsonl` memo payloads equal `flybrain:v1:<run>:<kind>:<sha256>[:<extra>]` for manifest, each category root, final decision and receipt, in chain order |

`software.source_sha256` differing from the verifier's own package is a **warning** (a newer verifier may check an older run); everything else is a failure.

## Audit bundle

The dashboard's `/api/bundle.zip` (or a copy of the run directory minus `launch/mock-ledger`) is everything a third party needs. Verification never consults the dashboard, the summary, or any database: `summary.json` is itself checked against the chain.
