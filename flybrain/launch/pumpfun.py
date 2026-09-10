"""Gate C: Pump.fun adapter, feature-gated until the official program/API is reviewed.

Warnings carried from the build brief:
- PumpPortal.fun is a third-party service, not an official Pump.fun API.
- Never send production signing keys to a third party.
- Only accept an endpoint that returns an *unsigned* transaction; validate and
  sign locally; pin program IDs; simulate before signing; verify the expected
  mint/metadata/pool accounts.
"""


class PumpFunAdapter:
    name = "pumpfun"
    network = "mainnet-beta"
    program_ids = ()

    def __init__(self, *_, **__):
        raise NotImplementedError("PumpFunAdapter is feature-gated until the official program/API review (Gate C)")
