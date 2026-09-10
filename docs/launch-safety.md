# Launch safety

## Where this build can launch

Nowhere real. The only working adapter is `MockLaunchAdapter` (`network = mock`). `SolanaDevnetMintAdapter` (Gate B), `PumpFunAdapter` (Gate C) and `PonsAdapter` (unidentified) refuse to construct. `LaunchSettings` defaults are `LIVE_LAUNCH=false`, `NETWORK=mock`, `MAX_SOL_SPEND=0.05`, `INITIAL_DEV_BUY=0`, and `LaunchGuard.check_settings` vetoes `LIVE_LAUNCH=true`, any mainnet network name, any network outside the allowlist, a cap above 1 SOL, and any dev buy that is not explicitly disclosed.

## Order of operations (`flybrain/launch/pipeline.py`)

1. `LaunchGuard.check_intent` — veto only. The intent must reference the recorded final decision hash; the decision must be `LAUNCH` with a complete identity and a fly-selected venue; total spend (cap + fees + rent + dev buy) must fit the cap.
2. `adapter.preflight` — read-only.
3. `adapter.build_unsigned` + `LaunchGuard.inspect_unsigned` — every program ID and instruction must be on the adapter's allowlist; the expected mint must be declared.
4. **Chain the intent** (`launch/intent.json`) before any network call.
5. Sign locally, submit.
6. `REJECTED` ⇒ chained receipt with status REJECTED, halt. `UNKNOWN` ⇒ no resubmission; reconcile by intent id; if unresolved, write `STOP` and halt. A second token is never created.
7. Chain the receipt, check mint == expected mint and on-venue metadata == the fly's identity, commit the receipt hash.

## Mainnet activation gate (not in this build)

Requires a separate explicit human approval after reviewing the exact name, ticker, metadata, wallet, venue, spend cap and a transaction simulation; jurisdiction-specific legal review of token-marketing, sanctions and consumer-protection obligations; an isolated low-balance signer or reviewed signing service; and equivalent preflight/inspection/reconciliation/test coverage for every venue offered to the fly. Until both venue adapters meet that bar, `venue_selection_mode` stays `simulation` and the manifest validator rejects anything else.

## Never

Seed phrases or keys in source, `.env.example`, logs, prompts or artifacts. Sending signing keys to a third party (PumpPortal is not an official Pump.fun API). Bundled insider wallets, wash volume, self-trading, undisclosed dev buys. Trading the project's own token. Replacing `WAIT` or `NO_DECISION` with `LAUNCH`.
