"""Canonical JSON bytes and SHA-256 for every committed artifact.

The encoding is the RFC 8785 (JCS) subset that needs no floating-point
serialization rules: object keys sorted by Unicode code point, no whitespace,
UTF-8, and **no floats**. Every measured quantity is carried as a decimal
string, so two independent implementations produce identical bytes. A float
anywhere in a committed structure is a programming error and raises.
"""

import hashlib
import json
from pathlib import Path


class CanonicalError(ValueError):
    pass


def _check(value, path="$"):
    if isinstance(value, bool) or value is None or isinstance(value, int):
        return
    if isinstance(value, float):
        raise CanonicalError(f"Float at {path}; use a decimal string")
    if isinstance(value, str):
        return
    if isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            _check(item, f"{path}[{i}]")
        return
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise CanonicalError(f"Non-string key at {path}")
            _check(v, f"{path}.{k}")
        return
    raise CanonicalError(f"Unsupported type {type(value).__name__} at {path}")


def canonical_bytes(value) -> bytes:
    _check(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(value) -> str:
    return sha256_hex(canonical_bytes(value))


def file_sha256(path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_canonical(path, value) -> str:
    """Atomically write canonical bytes; return their SHA-256."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_bytes(value)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_bytes(data)
    tmp.replace(path)
    return sha256_hex(data)


def load_canonical(path):
    """Load a committed artifact and return (value, sha256 of the exact bytes).

    The bytes on disk must already be canonical: re-encoding must reproduce
    them, otherwise the artifact was edited by hand or written by other code.
    """
    data = Path(path).read_bytes()
    value = json.loads(data.decode("utf-8"))
    if canonical_bytes(value) != data:
        raise CanonicalError(f"{path} is not in canonical form")
    return value, sha256_hex(data)


def decimal_str(x, places=6) -> str:
    """Fixed-point decimal string for a measured quantity."""
    return f"{float(x):.{places}f}"
