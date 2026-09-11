# What FLYBRAIN claims, and what it does not

## The one sentence we use

> The fly chose among a precommitted set of alternatives using a fixed, published neural decoding protocol. A pre-approved execution system submitted the resulting launch transaction.

Viral copy (“A fly brain launched a coin.”, “166,700 neurons. One terrible idea.”, “Forget AI. We have flies now.”, “The fly chose the coin. The chain keeps the receipts.”) must always appear next to that disclosure, and the manifest carries it verbatim in `disclosure`.

## Claims we make

- Every candidate (name, ticker, logo, palette, description, venue, launch/wait) was authored by people and finalized in a canonical JSON manifest whose SHA-256 is recorded before the first trial.
- Each A-vs-B match is decided only by the fixed rule in `flybrain/choice/decoder.py`: mean DNp20-left rate minus mean DNp20-right rate, mirrored presentation, averaged, compared to a published threshold, gated on DNpe017 spikes. No other code interprets spikes.
- Each trial's exact RGB input, spike counts, checkpoint hash, decoder cell IDs and rates are recorded in a hash-chained envelope; `flybrain verify-run` recomputes all of it and fails on a one-bit change.
- Persistent side bias cannot decide a match (it cancels in the mirrored score). Inconclusive matches exhaust their predeclared attempts and end in `NO_DECISION`. `WAIT`, `NO_DECISION`, vetoes and failed launches are kept in the public record.
- The experiment can end without a token, and that outcome is a first-class result.

## Claims we do not make

- That the connectome invented language, understood money, formed intentions, is conscious, or experiences reward or pain.
- That the simulated network learned anything, trades profitably, or is a “scientifically proven trader”. Identity selection runs with plasticity frozen and no reinforcement.
- That the retained MaleCNS graph reproduces biological fly behavior or vision. Transmitter signs, LIF photoreceptors and the RGB adapter are modeling assumptions (see `docs/model.md`).
- Any return, price support, buyback, profit or “guaranteed” anything.
- That a **fixture-backend** run says anything about the connectome. The fixture is a deterministic stand-in for exercising the protocol and audit trail; every artifact it produces is labeled `fixture-brain-v1`.
- That PumpPortal or any third-party endpoint is an official Pump.fun API, or that FLYBRAIN is affiliated with or endorsed by pons.

## What an LLM may do

Summarize a completed, verified run in plain English, disclosed as a presentation layer. It may never choose, rerank, reinterpret, or replace a recorded result. This build uses no LLM anywhere.

## Market-integrity rules (mandatory)

No bundled insider wallets, secret allocations, fake users, wash volume, self-trading, volume bots, sniper coordination or undisclosed dev buys. The fly must never trade its own token. Creator allocation, fees, treasury wallets and routing are displayed before launch. Mainnet legality, sanctions, consumer-protection and token-marketing obligations require jurisdiction-specific professional review; the software surfaces this as a gate (`docs/launch-safety.md`), it does not assume permission.
