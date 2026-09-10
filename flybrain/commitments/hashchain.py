"""Append-only hash chain over the run's committed artifacts.

Every artifact carries ``previous_sha256`` (the hash of the artifact before it)
so its own hash covers the whole history. ``chain.jsonl`` is an index only; the
verifier recomputes every link from the referenced files.
"""

import json
from pathlib import Path

from .canonical import canonical_bytes, file_sha256, sha256_hex, write_canonical

GENESIS = "0" * 64


class HashChain:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.index = self.root / "chain.jsonl"
        self.entries = []
        if self.index.exists():
            with self.index.open() as f:
                self.entries = [json.loads(line) for line in f if line.strip()]

    @property
    def head(self) -> str:
        return self.entries[-1]["sha256"] if self.entries else GENESIS

    @property
    def seq(self) -> int:
        return len(self.entries)

    def append(self, kind: str, relative_path: str, artifact: dict) -> str:
        """Write ``artifact`` (with previous link) and index it. Returns its hash."""
        if "previous_sha256" in artifact and artifact["previous_sha256"] != self.head:
            raise ValueError("Artifact previous link does not match chain head")
        artifact = {**artifact, "previous_sha256": self.head, "chain_seq": self.seq}
        digest = write_canonical(self.root / relative_path, artifact)
        entry = {
            "seq": self.seq,
            "kind": kind,
            "path": relative_path,
            "sha256": digest,
            "previous_sha256": artifact["previous_sha256"],
        }
        with self.index.open("a") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")
        self.entries.append(entry)
        return digest

    def roots(self) -> dict:
        """Chain head after each ``category_result`` entry, keyed by category."""
        out = {}
        for e in self.entries:
            if e["kind"] == "category_result":
                out[e["path"]] = e["sha256"]
        return out


def walk(root: Path):
    """Yield (entry, artifact, sha256) in order, checking every link.

    Raises ValueError on the first sequence, hash or link mismatch.
    """
    root = Path(root)
    index = root / "chain.jsonl"
    if not index.exists():
        raise ValueError("chain.jsonl missing")
    previous = GENESIS
    with index.open() as f:
        lines = [line for line in f if line.strip()]
    for expected_seq, line in enumerate(lines):
        entry = json.loads(line)
        if entry.get("seq") != expected_seq:
            raise ValueError(f"Chain sequence gap at {expected_seq}")
        path = root / entry["path"]
        if not path.is_relative_to(root):
            raise ValueError("Chain path escapes run directory")
        data = path.read_bytes()
        digest = sha256_hex(data)
        if digest != entry["sha256"]:
            raise ValueError(f"Chain hash mismatch at seq {expected_seq}: {entry['path']}")
        artifact = json.loads(data.decode("utf-8"))
        if canonical_bytes(artifact) != data:
            raise ValueError(f"Non-canonical artifact at seq {expected_seq}")
        if artifact.get("previous_sha256") != previous or entry["previous_sha256"] != previous:
            raise ValueError(f"Chain link mismatch at seq {expected_seq}")
        if artifact.get("chain_seq") != expected_seq:
            raise ValueError(f"Artifact seq mismatch at {expected_seq}")
        yield entry, artifact, digest
        previous = digest


__all__ = ["HashChain", "walk", "GENESIS", "file_sha256"]
