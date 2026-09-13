import json

from flybrain.dashboard import export_party
from flybrain.games import beerpong
from tests.conftest import write_fixture_checkpoint


def test_export_party_is_self_contained(tmp_path):
    cp = write_fixture_checkpoint(tmp_path)
    beerpong.play("fixture-brain-v1", cp, tmp_path / "g", run_id="export-test", log=lambda *_: None)
    out = export_party(tmp_path / "g", tmp_path / "site", cname="flypong.xyz")
    html = (out / "index.html").read_text()
    assert "FLYPONG" in html and 'src="static/party/party.js"' in html and "/static/" not in html
    for rel in ["static/party/party.js", "static/party/party.css", "static/flylib.js", "static/vendor/three.min.js", "run/chain.jsonl", "run/brain/atlas.json", "run/brain/positions.f32", "api/index.json", "CNAME", ".nojekyll"]:
        assert (out / rel).exists(), rel
    idx = json.loads((out / "api" / "index.json").read_text())
    assert idx["chain_error"] is None and idx["chain"][0]["kind"] == "pong_header"
    js = (out / "static" / "party" / "party.js").read_text()
    assert 'fetch("api/index.json")' in js and '"/run/"' not in js and '"/api/' not in js
    assert (out / "CNAME").read_text().strip() == "flypong.xyz"
    assert not (out / "party.js").exists() and not (out / "party.css").exists()
