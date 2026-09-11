# pons: what it is and what that changes

Source: https://docs.ponsfamily.com (v1 at `/docs`, v2 at `/docs/v2`), read 2026-09-11. pons asks integrators to write its name in lowercase, link to the app, and not imply partnership or endorsement without a written agreement. FLYBRAIN has no agreement with pons.

## Findings

- **Chain.** pons runs on **Robinhood Chain, chain id 4663** (EVM; native ETH; public RPC `https://rpc.mainnet.chain.robinhood.com`; explorer `robinhoodchain.blockscout.com`). It is not a Solana launchpad. A fly choice of pons over Pump.fun is therefore also a choice of chain, and the Solana Memo commitment plan needs an EVM counterpart (calldata memo or an event-emitting commitment contract) for a pons launch.
- **v1** (active factory `0xA5aAb3F0c6EeadF30Ef1D3Eb997108E976351feB`): token + Uniswap V3 pool against WETH in one transaction, 1e9 fixed supply, 1% pool fee, 0.0005 ETH launch fee, creator/protocol fee split 70/30, graduation at 4.2 ETH paired. Launch-window limits: creator-only buy on the launch block, 5% hold / 5.5% buy caps for two blocks.
- **v2** (factory `0x7eD598BcEf8bd9Edd8C97A195C6d13f40801EC7e`, plus hook, escrow, buyback vault, locker, launch-and-buy, deployer, graduation executor/guard): bonding curve first, Uniswap v4 pool at graduation with permanently locked liquidity. One payable call:

  ```
  launchToken(TokenParams params, uint256 launchConfigId, address pairToken) payable
  TokenParams { name, symbol, logo, description, Socials socials, address creatorFeeRecipient,
                uint16 creatorTaxBps, bool buybackEnabled, bytes32 expectedEconomics, bytes32 salt }
  ```

  The launch fee is `msg.value` and must be read from `launchFee()`. `expectedEconomics` must be the result of `previewLaunchEconomics(launchConfigId, pairToken)` fetched right before the call, or the launch reverts with `LaunchEconomicsMismatch`. `salt` drives CREATE2 for the token and curve addresses. Snipe tax: 99% decaying to 0 over the first 5 seconds; the launching address and creator fee recipient are exempt.
- **No HTTP API** in the trust path; integration is onchain reads and event indexing (`TokenLaunched`, `CurveBuy`, `CurveSell`, `PoolGraduated`).
- **No testnet deployment exists.**
- **v2 is unaudited** until reports (SB Security, Dingbats, Pashov) are published.
- Custom errors include `NotWhitelisted`, so launching may be gated; contact `contact@ponsfamily.com` for integration/early access.

## What this build does

`flybrain/launch/pons.py` implements `LaunchAdapter` for pons v2 as **build and inspect only**:

- Encodes `launchToken` calldata locally (dependency-free keccak + ABI encoder in `flybrain/launch/evm.py`, known-answer tested), with `creatorTaxBps = 0`, `buybackEnabled = false` (the project must never buy its own token), empty socials, and `salt = keccak256("flybrain:pons:salt:" + final_decision_sha256)` so the eventual token address is bound to the recorded choice.
- `preflight` is read-only. Offline it fails on the unread fee and economics pin; with `--rpc` it reads `eth_chainId`, factory code, `launchFee()`, `previewLaunchEconomics` and `launchConfigCount()`. The audit and testnet checks fail by design in this build.
- `inspect` re-encodes calldata from the decoded parameters and checks target, chain id, value, pin, identity fields, tax/buyback flags and salt derivation.
- `submit` always returns `REJECTED`; `reconcile` returns `None`. Only read-only JSON-RPC methods are callable.
- `flybrain pons-preview --run <dir> [--rpc URL] --creator-fee-recipient 0x…` writes `launch/pons-preview.json` for human review (Gate D style export). Exit code is nonzero unless preflight passes and inspection is clean, which cannot happen in this build.

## Before pons could be offered for real

Published and reviewed audits; a written integration/attribution agreement; a disclosed treasury as `creatorFeeRecipient`; a hosted logo URI; an EVM commitment path equivalent to the Solana memos; a `predictLaunchAddresses` signature (or post-launch `TokenLaunched` indexing) for `expected_mint`; equivalent preflight, inspection, reconciliation and test coverage to the Pump.fun adapter; and the separate explicit human approval described in `docs/launch-safety.md`. Until then `venue_selection_mode` stays `simulation`.
