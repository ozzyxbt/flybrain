import json

import pytest

from flybrain.choice import font, manifest as mm
from flybrain.commitments.canonical import CanonicalError, canonical_bytes, canonical_sha256, load_canonical, write_canonical
from tests.conftest import FIXTURE_CHECKPOINT, GENESIS, small_manifest


def test_canonical_sorted_compact_and_float_free():
    assert canonical_bytes({"b": 1, "a": [True, None, "x"]}) == b'{"a":[true,null,"x"],"b":1}'
    with pytest.raises(CanonicalError):
        canonical_bytes({"x": 1.5})
    assert canonical_sha256({"a": 1, "b": 2}) == canonical_sha256({"b": 2, "a": 1})


def test_load_rejects_non_canonical_bytes(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('{"b": 1, "a": 2}')
    with pytest.raises(CanonicalError):
        load_canonical(p)
    write_canonical(p, {"b": 1, "a": 2})
    value, digest = load_canonical(p)
    assert value == {"a": 2, "b": 1} and len(digest) == 64


def test_genesis_manifest_valid_and_hash_stable():
    m, digest = mm.load(GENESIS)
    assert digest == canonical_sha256(m)
    assert (GENESIS.parent / "genesis-v1.draft.json").exists()
    draft = json.loads((GENESIS.parent / "genesis-v1.draft.json").read_text())
    draft["brain_checkpoint_sha256"] = m["brain_checkpoint_sha256"]
    assert canonical_sha256(mm.validate(draft)) == digest, "canonical file must match the draft"
    assert m["brain_checkpoint_sha256"] == __import__("flybrain.commitments.canonical", fromlist=["file_sha256"]).file_sha256(FIXTURE_CHECKPOINT)


def test_reordered_candidates_change_the_hash():
    m = small_manifest(FIXTURE_CHECKPOINT)
    a = canonical_sha256(mm.validate(m))
    m["categories"]["name"].reverse()
    assert canonical_sha256(mm.validate(m)) != a


@pytest.mark.parametrize(
    "mutate,message",
    [
        (lambda m: m["categories"]["name"].__setitem__(0, {"id": "n-a", "text": "OFFICIAL DOGE"}), "blocked term"),
        (lambda m: m["categories"]["name"].__setitem__(0, {"id": "n-a", "text": "FLÿ"}), "unsupported characters"),
        (lambda m: m["categories"]["ticker"].__setitem__(0, {"id": "t-a", "text": "fly"}), "uppercase"),
        (lambda m: m.__setitem__("learning_frozen", False), "learning_frozen"),
        (lambda m: m.__setitem__("venue_selection_mode", "live"), "simulation"),
        (lambda m: m.__setitem__("decoder_threshold_hz", 2.0), "decimal string"),
        (lambda m: m["categories"]["launch_action"].reverse(), "launch_action"),
        (lambda m: m["categories"]["name"].append({"id": "n-a", "text": "DUPE"}), "duplicate id"),
        (lambda m: m.__setitem__("baseline_commit", "deadbeef"), "baseline_commit"),
    ],
)
def test_manifest_validation_rejects(mutate, message):
    m = small_manifest(FIXTURE_CHECKPOINT)
    mutate(m)
    with pytest.raises(mm.ManifestError, match=message):
        mm.validate(m)


def test_font_covers_manifest_text():
    m, _ = mm.load(GENESIS)
    for cat in mm.TEXT_CATEGORIES:
        for c in m["categories"][cat]:
            assert font.supported(c["text"])
    assert font.text_width("AB", 2) == 22 and font.wrap("ONE TWO THREE", 7) == ["ONE TWO", "THREE"]
