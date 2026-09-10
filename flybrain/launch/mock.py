"""Deterministic mock launch adapter for Gate A and tests.

The mint address is derived from the intent hash, so a verifier recomputes it
without trusting the receipt. Nothing here touches a network or a key.
"""

import hashlib
import json
from pathlib import Path

from ..commitments.canonical import canonical_bytes, sha256_hex
from .base import FinalLaunchReceipt, PreflightResult, SubmissionResult, UnsignedTransaction

PROGRAM_ID = "mock-launch-v1"
ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def base58(data: bytes) -> str:
    n = int.from_bytes(data, "big")
    out = ""
    while n:
        n, r = divmod(n, 58)
        out = ALPHABET[r] + out
    pad = len(data) - len(data.lstrip(b"\0"))
    return "1" * pad + out


def mock_mint(intent_sha256: str) -> str:
    return base58(hashlib.sha256(b"flybrain-mock-mint:" + intent_sha256.encode()).digest())


def mock_signature(payload_sha256: str) -> str:
    return base58(hashlib.sha256(b"flybrain-mock-sig:" + payload_sha256.encode()).digest() * 2)


class MockSigner:
    def sign(self, unsigned: UnsignedTransaction) -> bytes:
        return b"MOCKSIG:" + unsigned.payload


class MockLaunchAdapter:
    name = "mock"
    network = "mock"
    program_ids = (PROGRAM_ID,)

    def __init__(self, ledger_dir, fail_submit: str | None = None):
        self.ledger = Path(ledger_dir)
        self.ledger.mkdir(parents=True, exist_ok=True)
        self.fail_submit = fail_submit  # None | "unknown" | "rejected"
        self.submissions = 0

    def preflight(self, intent: dict) -> PreflightResult:
        checks = [
            {"check": "network", "ok": intent["network"] == self.network, "detail": intent["network"]},
            {"check": "wallet_balance", "ok": True, "detail": "simulated; no wallet"},
            {"check": "venue_supported", "ok": intent["venue"] in ("pumpfun", "pons"), "detail": f"{intent['venue']} (simulated)"},
            {"check": "no_prior_mint_for_intent", "ok": not (self.ledger / f"{intent['intent_id']}.json").exists(), "detail": intent["intent_id"]},
        ]
        return PreflightResult(all(c["ok"] for c in checks), self.network, checks)

    def build_unsigned(self, intent: dict) -> UnsignedTransaction:
        payload = canonical_bytes({"intent": intent, "program": PROGRAM_ID})
        intent_sha = sha256_hex(canonical_bytes(intent))
        mint = mock_mint(intent_sha)
        instructions = [
            {"program_id": PROGRAM_ID, "name": "create_mint", "accounts": [mint, "mock-payer"], "data": {"decimals": 6}},
            {"program_id": PROGRAM_ID, "name": "set_metadata", "accounts": [mint], "data": {"name": intent["name"], "symbol": intent["ticker"]}},
            {"program_id": PROGRAM_ID, "name": "revoke_mint_authority", "accounts": [mint], "data": {}},
            {"program_id": PROGRAM_ID, "name": "revoke_freeze_authority", "accounts": [mint], "data": {}},
        ]
        return UnsignedTransaction([PROGRAM_ID], instructions, mint, payload, sha256_hex(payload))

    def submit(self, signed_transaction: bytes) -> SubmissionResult:
        self.submissions += 1
        if not signed_transaction.startswith(b"MOCKSIG:"):
            return SubmissionResult("REJECTED", None, "unsigned payload")
        payload = signed_transaction[len(b"MOCKSIG:") :]
        body = json.loads(payload.decode("utf-8"))
        intent = body["intent"]
        intent_sha = sha256_hex(canonical_bytes(intent))
        record = {"intent": intent, "intent_sha256": intent_sha, "mint": mock_mint(intent_sha), "signature": mock_signature(sha256_hex(payload))}
        path = self.ledger / f"{intent['intent_id']}.json"
        if path.exists():
            return SubmissionResult("REJECTED", None, "duplicate intent")
        if self.fail_submit == "rejected":
            return SubmissionResult("REJECTED", None, "simulated rejection")
        path.write_text(json.dumps(record, indent=2))
        if self.fail_submit == "unknown":
            return SubmissionResult("UNKNOWN", None, "simulated lost response after acceptance")
        return SubmissionResult("CONFIRMED", record["signature"])

    def reconcile(self, intent_id: str):
        path = self.ledger / f"{intent_id}.json"
        if not path.exists():
            return None
        r = json.loads(path.read_text())
        i = r["intent"]
        return FinalLaunchReceipt(
            intent_id=intent_id,
            intent_sha256=r["intent_sha256"],
            network=self.network,
            venue=i["venue"],
            mint=r["mint"],
            signature=r["signature"],
            metadata={"name": i["name"], "symbol": i["ticker"], "description": i["description"], "logo_png_sha256": i["logo_png_sha256"], "palette": i["palette"]},
            authorities={"mint": None, "freeze": None, "update": None},
            creator_allocation_percent=i["creator_allocation_percent"],
            creator_fee_disclosure=i["creator_fee_disclosure"],
            explorer_url=None,
            simulated=True,
        )
