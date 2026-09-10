"""Launch adapter interface. Every venue sits behind exactly this surface.

    preflight      read-only checks; never signs, never submits
    build_unsigned returns a fully inspectable unsigned transaction
    submit         takes signed bytes; returns CONFIRMED / UNKNOWN / REJECTED
    reconcile      resolves an intent by id/mint; never creates a second token

Intents and receipts are plain dicts so they can be canonicalized and chained.
"""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class PreflightResult:
    ok: bool
    network: str
    checks: list = field(default_factory=list)

    def to_dict(self):
        return {"ok": self.ok, "network": self.network, "checks": list(self.checks)}


@dataclass(frozen=True)
class UnsignedTransaction:
    program_ids: list
    instructions: list
    expected_mint: str
    payload: bytes
    payload_sha256: str

    def to_dict(self):
        return {
            "program_ids": list(self.program_ids),
            "instructions": list(self.instructions),
            "expected_mint": self.expected_mint,
            "payload_sha256": self.payload_sha256,
        }


@dataclass(frozen=True)
class SubmissionResult:
    status: str  # CONFIRMED | UNKNOWN | REJECTED
    signature: str | None
    detail: str = ""

    def to_dict(self):
        return {"status": self.status, "signature": self.signature, "detail": self.detail}


@dataclass(frozen=True)
class FinalLaunchReceipt:
    intent_id: str
    intent_sha256: str
    network: str
    venue: str
    mint: str
    signature: str
    metadata: dict
    authorities: dict
    creator_allocation_percent: str
    creator_fee_disclosure: str
    explorer_url: str | None
    simulated: bool

    def to_dict(self):
        return {
            "intent_id": self.intent_id,
            "intent_sha256": self.intent_sha256,
            "network": self.network,
            "venue": self.venue,
            "mint": self.mint,
            "signature": self.signature,
            "metadata": dict(self.metadata),
            "authorities": dict(self.authorities),
            "creator_allocation_percent": self.creator_allocation_percent,
            "creator_fee_disclosure": self.creator_fee_disclosure,
            "explorer_url": self.explorer_url,
            "simulated": self.simulated,
        }


class LaunchAdapter(Protocol):
    name: str
    network: str
    program_ids: tuple

    def preflight(self, intent: dict) -> PreflightResult: ...
    def build_unsigned(self, intent: dict) -> UnsignedTransaction: ...
    def submit(self, signed_transaction: bytes) -> SubmissionResult: ...
    def reconcile(self, intent_id: str) -> FinalLaunchReceipt | None: ...


class Signer(Protocol):
    def sign(self, unsigned: UnsignedTransaction) -> bytes: ...


def build_intent(final: dict, final_sha256: str, manifest: dict, run_id: str, settings, logo_png_sha256: str) -> dict:
    """Compose the launch intent purely from the recorded final decision."""
    from ..choice.manifest import candidate

    ident = final["identity"]
    name = candidate(manifest, "name", ident["name"])["text"]
    ticker = candidate(manifest, "ticker", ident["ticker"])["text"]
    description = candidate(manifest, "description", ident["description"])["text"]
    palette = candidate(manifest, "palette", ident["palette"])
    return {
        "intent_id": f"{run_id}-launch-1",
        "run_id": run_id,
        "final_decision_sha256": final_sha256,
        "manifest_sha256": final["manifest_sha256"],
        "name": name,
        "ticker": ticker,
        "description": description,
        "logo_id": ident["logo"],
        "logo_png_sha256": logo_png_sha256,
        "palette_id": ident["palette"],
        "palette": list(palette["colors"]),
        "venue": final["launch_venue"],
        "network": settings.network,
        "max_sol_spend": settings.max_sol_spend,
        "initial_dev_buy_sol": settings.initial_dev_buy_sol,
        "estimated_fees_sol": "0",
        "metadata_rent_sol": "0",
        "creator_allocation_percent": "0",
        "creator_fee_disclosure": "Any creator fee is routed to the disclosed treasury; none configured in this build.",
        "treasury_wallet": None,
        "insider_wallets": [],
        "disclosure": manifest["disclosure"],
    }
