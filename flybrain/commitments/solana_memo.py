"""Compact public commitments, formatted for the Solana Memo program.

Gate A records commitments locally (``commitments.jsonl``) with the exact memo
payload a later devnet/mainnet committer would submit. No network access here.
Memo program reference: https://www.solana-program.com/docs/memo
"""

import json
import time
from pathlib import Path
from typing import Protocol

MEMO_PROGRAM_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
PREFIX = "flybrain"


def memo_payload(kind: str, sha256: str, run_id: str, extra: str = "") -> str:
    if len(sha256) != 64 or any(c not in "0123456789abcdef" for c in sha256):
        raise ValueError("Commitment must be a lowercase hex SHA-256")
    parts = [PREFIX, "v1", run_id, kind, sha256]
    if extra:
        parts.append(extra)
    payload = ":".join(parts)
    if len(payload.encode()) > 566:  # Memo v2 practical limit inside one tx
        raise ValueError("Memo payload too long")
    return payload


class Committer(Protocol):
    def commit(self, kind: str, sha256: str, extra: str = "") -> dict: ...


class LocalCommitter:
    """Records what would be published. Used by Gate A and by tests."""

    def __init__(self, root: Path, run_id: str):
        self.path = Path(root) / "commitments.jsonl"
        self.run_id = run_id

    def commit(self, kind: str, sha256: str, extra: str = "") -> dict:
        record = {
            "kind": kind,
            "sha256": sha256,
            "memo": memo_payload(kind, sha256, self.run_id, extra),
            "network": "local",
            "program_id": MEMO_PROGRAM_ID,
            "signature": None,
            "wall_time": time.time(),
        }
        with self.path.open("a") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")
        return record


class SolanaMemoCommitter:
    """Gate B. Deliberately unimplemented in Gate A: no RPC, no signer."""

    def __init__(self, *_, **__):
        raise NotImplementedError(
            "On-chain memo commitments are Gate B. Gate A records commitments locally."
        )


def read_commitments(root: Path) -> list:
    path = Path(root) / "commitments.jsonl"
    if not path.exists():
        return []
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]
