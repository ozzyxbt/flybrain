"""Precommitted candidate manifest: loading, validation and canonical hashing.

The manifest is finalized and its hash published *before* any neural
evaluation. Everything the fly can be shown is authored here; the fly selects
among these candidates, it does not generate them.
"""

import re
from pathlib import Path

from .. import BASELINE_COMMIT, PROTOCOL
from ..commitments.canonical import canonical_sha256, load_canonical
from . import font

CATEGORIES = (
    "name",
    "ticker",
    "logo",
    "palette",
    "description",
    "launch_venue",
    "launch_action",
)
TEXT_CATEGORIES = ("name", "ticker", "description", "launch_venue", "launch_action")
VARIANTS = ("standard", "high_contrast", "large")
HEX = re.compile(r"^#[0-9a-f]{6}$")
ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
LOGO_SIZE = 8
# Content policy: candidate text must not impersonate or reference these. The
# list is a floor, not a substitute for human review of the manifest.
BLOCKED_TERMS = (
    "COINBASE",
    "SOLANA",
    "PUMP.FUN",
    "PUMPFUN",
    "JANELIA",
    "GOOGLE",
    "ELON",
    "MUSK",
    "TRUMP",
    "DOGE",
    "PEPE",
    "BONK",
    "SHIB",
    "BITCOIN",
    "ETHEREUM",
    "OFFICIAL",
    "GUARANTEED",
    "100X",
    "1000X",
)


class ManifestError(ValueError):
    pass


def _require(condition, message):
    if not condition:
        raise ManifestError(message)


def _check_text(value, field, max_len, policy=True):
    _require(isinstance(value, str) and value.strip() == value and value, f"{field}: text required")
    _require(len(value) <= max_len, f"{field}: longer than {max_len}")
    _require(
        font.supported(value),
        f"{field}: unsupported characters {font.unsupported_characters(value)!r}",
    )
    if not policy:
        return
    upper = value.upper()
    for term in BLOCKED_TERMS:
        _require(term not in upper, f"{field}: blocked term {term!r}")


def validate(m: dict) -> dict:
    _require(isinstance(m, dict), "Manifest must be an object")
    _require(m.get("protocol") == PROTOCOL, f"protocol must be {PROTOCOL}")
    _require(m.get("baseline_commit") == BASELINE_COMMIT, "baseline_commit mismatch")
    _require(ID.match(m.get("manifest_id", "")), "manifest_id required")
    cp = m.get("brain_checkpoint_sha256")
    _require(isinstance(cp, str) and re.fullmatch(r"[0-9a-f]{64}", cp), "brain_checkpoint_sha256 required")
    _require(m.get("learning_frozen") is True, "learning_frozen must be true for identity selection")
    _require(m.get("backend") in ("fixture-brain-v1", "malecns-connectome"), "backend unknown")
    w = m.get("neural_window_ms")
    _require(isinstance(w, int) and 10 <= w <= 5000, "neural_window_ms must be an int in 10..5000")
    thr = m.get("decoder_threshold_hz")
    _require(isinstance(thr, str) and re.fullmatch(r"\d+(\.\d+)?", thr) and float(thr) > 0, "decoder_threshold_hz decimal string > 0")
    attempts = m.get("max_attempts_per_match")
    _require(isinstance(attempts, int) and 1 <= attempts <= 5, "max_attempts_per_match 1..5")
    variants = m.get("attempt_variants")
    _require(
        isinstance(variants, list) and len(variants) == attempts and all(v in VARIANTS for v in variants) and len(set(variants)) == attempts,
        "attempt_variants must list one distinct known variant per attempt",
    )
    frame = m.get("frame")
    _require(frame == {"width": 320, "height": 180}, "frame must be 320x180 (retinal projection assumption)")
    lw = m.get("launch_windows")
    _require(
        isinstance(lw, dict) and isinstance(lw.get("max_windows"), int) and 1 <= lw["max_windows"] <= 10 and isinstance(lw.get("interval_seconds"), int) and lw["interval_seconds"] >= 60,
        "launch_windows.max_windows 1..10 and interval_seconds >= 60",
    )
    _require(m.get("category_order") == list(CATEGORIES), "category_order must be the fixed protocol order")
    cats = m.get("categories")
    _require(isinstance(cats, dict) and set(cats) == set(CATEGORIES), "categories must cover exactly the protocol categories")
    seen_ids = set()
    for cat in CATEGORIES:
        items = cats[cat]
        _require(isinstance(items, list) and 2 <= len(items) <= 16, f"{cat}: 2..16 candidates")
        for i, c in enumerate(items):
            field = f"{cat}[{i}]"
            _require(isinstance(c, dict) and ID.match(c.get("id", "")), f"{field}: id required")
            _require(c["id"] not in seen_ids, f"{field}: duplicate id {c['id']}")
            seen_ids.add(c["id"])
            if cat in TEXT_CATEGORIES:
                limit = {"name": 16, "ticker": 8, "description": 72, "launch_venue": 12, "launch_action": 8}[cat]
                # Venue/action labels name the venue itself; the brand policy
                # applies to the token identity candidates.
                _check_text(c.get("text"), field, limit, policy=cat not in ("launch_venue", "launch_action"))
                _require(set(c) <= {"id", "text"}, f"{field}: unexpected keys")
            elif cat == "logo":
                _check_text(c.get("label", ""), field + ".label", 16)
                px = c.get("pixels")
                _require(
                    isinstance(px, list) and len(px) == LOGO_SIZE and all(isinstance(r, str) and len(r) == LOGO_SIZE and set(r) <= {"#", "."} for r in px),
                    f"{field}: pixels must be {LOGO_SIZE} rows of {LOGO_SIZE} '#'/'.' characters",
                )
                _require(HEX.match(c.get("fg", "")) and HEX.match(c.get("bg", "")), f"{field}: fg/bg hex colors")
                _require(set(c) <= {"id", "label", "pixels", "fg", "bg"}, f"{field}: unexpected keys")
            elif cat == "palette":
                _check_text(c.get("label", ""), field + ".label", 16)
                colors = c.get("colors")
                _require(isinstance(colors, list) and 3 <= len(colors) <= 5 and all(isinstance(x, str) and HEX.match(x) for x in colors), f"{field}: 3..5 hex colors")
                _require(set(c) <= {"id", "label", "colors"}, f"{field}: unexpected keys")
        if cat == "ticker":
            for c in items:
                _require(c["text"].isalnum() and c["text"].isupper(), f"{cat}: tickers are uppercase alphanumerics")
    _require([c["id"] for c in cats["launch_action"]] == ["launch", "wait"], "launch_action must be exactly [launch, wait]")
    _require({c["id"] for c in cats["launch_venue"]} == {"pumpfun", "pons"}, "launch_venue must be exactly {pumpfun, pons}")
    _require(isinstance(m.get("disclosure"), str) and "selected" in m["disclosure"], "disclosure text required")
    _require(m.get("venue_selection_mode") == "simulation", "venue_selection_mode must be 'simulation' until both adapters are verified")
    return m


def load(path) -> tuple:
    """Return (manifest, sha256). The file must be in canonical form."""
    value, digest = load_canonical(Path(path))
    validate(value)
    return value, digest


def digest(m: dict) -> str:
    return canonical_sha256(validate(m))


def candidates(m: dict, category: str) -> list:
    return list(m["categories"][category])


def candidate(m: dict, category: str, cid: str) -> dict:
    for c in m["categories"][category]:
        if c["id"] == cid:
            return c
    raise ManifestError(f"Unknown candidate {cid} in {category}")
