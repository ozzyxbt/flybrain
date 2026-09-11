"""Minimal, dependency-free EVM helpers: keccak-256 and ABI encoding.

Only what the pons adapter needs to build and inspect a ``launchToken``
calldata locally. Known-answer tests pin keccak and the encoder; anything
this module cannot encode raises rather than guessing.
"""

# ----------------------------------------------------------------- keccak
_RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]
_ROT = [
    [0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61], [28, 55, 25, 21, 56], [27, 20, 39, 8, 14],
]
_MASK = (1 << 64) - 1


def _rol(x, n):
    n %= 64
    return ((x << n) | (x >> (64 - n))) & _MASK if n else x


def _keccak_f(a):
    for rc in _RC:
        c = [a[x][0] ^ a[x][1] ^ a[x][2] ^ a[x][3] ^ a[x][4] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rol(c[(x + 1) % 5], 1) for x in range(5)]
        a = [[a[x][y] ^ d[x] for y in range(5)] for x in range(5)]
        b = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                b[y][(2 * x + 3 * y) % 5] = _rol(a[x][y], _ROT[x][y])
        a = [[b[x][y] ^ ((~b[(x + 1) % 5][y]) & b[(x + 2) % 5][y]) for y in range(5)] for x in range(5)]
        a[0][0] ^= rc
    return a


def keccak256(data: bytes) -> bytes:
    rate = 136
    padded = bytearray(data)
    padded.append(0x01)
    while len(padded) % rate:
        padded.append(0)
    padded[-1] |= 0x80
    a = [[0] * 5 for _ in range(5)]
    for off in range(0, len(padded), rate):
        block = padded[off : off + rate]
        for i in range(rate // 8):
            a[i % 5][i // 5] ^= int.from_bytes(block[i * 8 : i * 8 + 8], "little")
        a = _keccak_f(a)
    out = b""
    for i in range(4):
        out += a[i % 5][i // 5].to_bytes(8, "little")
    return out


def selector(signature: str) -> bytes:
    return keccak256(signature.encode())[:4]


# ------------------------------------------------------------ ABI encoding
def _is_dynamic(t) -> bool:
    if isinstance(t, tuple):
        return any(_is_dynamic(x) for x in t)
    return t in ("string", "bytes")


def _enc_static(t, v) -> bytes:
    if t == "address":
        if not (isinstance(v, str) and v.startswith("0x") and len(v) == 42):
            raise ValueError("address must be 0x + 40 hex")
        return bytes.fromhex(v[2:]).rjust(32, b"\0")
    if t.startswith("uint"):
        bits = int(t[4:] or 256)
        if not isinstance(v, int) or v < 0 or v >= 1 << bits:
            raise ValueError(f"{t} out of range")
        return v.to_bytes(32, "big")
    if t == "bool":
        return (1 if v else 0).to_bytes(32, "big")
    if t == "bytes32":
        if not isinstance(v, bytes) or len(v) != 32:
            raise ValueError("bytes32 must be 32 bytes")
        return v
    raise ValueError(f"unsupported static type {t}")


def _enc_dynamic(t, v) -> bytes:
    if t in ("string", "bytes"):
        raw = v.encode("utf-8") if t == "string" else v
        pad = (-len(raw)) % 32
        return len(raw).to_bytes(32, "big") + raw + b"\0" * pad
    raise ValueError(f"unsupported dynamic type {t}")


def encode(types, values) -> bytes:
    """ABI-encode a tuple. ``types`` items are strings or nested tuples of types."""
    if len(types) != len(values):
        raise ValueError("arity mismatch")
    heads, tails = [], []
    # Dynamic items take a 32-byte offset in the head; static tuples occupy
    # their full encoded width; other static items take 32 bytes.
    head_size = sum((len(encode(t, v)) if isinstance(t, tuple) and not _is_dynamic(t) else 32) for t, v in zip(types, values))
    offset = head_size
    for t, v in zip(types, values):
        if isinstance(t, tuple):
            enc = encode(t, v)
            if _is_dynamic(t):
                heads.append(offset.to_bytes(32, "big"))
                tails.append(enc)
                offset += len(enc)
            else:
                heads.append(enc)
        elif _is_dynamic(t):
            enc = _enc_dynamic(t, v)
            heads.append(offset.to_bytes(32, "big"))
            tails.append(enc)
            offset += len(enc)
        else:
            heads.append(_enc_static(t, v))
    return b"".join(heads) + b"".join(tails)


def canonical_type(t) -> str:
    if isinstance(t, tuple):
        return "(" + ",".join(canonical_type(x) for x in t) + ")"
    return t


def encode_call(name: str, types, values) -> bytes:
    sig = f"{name}({','.join(canonical_type(t) for t in types)})"
    return selector(sig) + encode(types, values)


def to_checksum(address: str) -> str:
    """EIP-55 checksum encoding."""
    addr = address.lower().replace("0x", "")
    if len(addr) != 40 or any(c not in "0123456789abcdef" for c in addr):
        raise ValueError("invalid address")
    h = keccak256(addr.encode()).hex()
    return "0x" + "".join(c.upper() if int(h[i], 16) >= 8 else c for i, c in enumerate(addr))
