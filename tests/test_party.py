import json
import urllib.request

from flybrain.dashboard import serve
from flybrain.games import beerpong
from tests.conftest import write_fixture_checkpoint


def get(url):
    with urllib.request.urlopen(url) as r:
        return r.status, r.read()


def test_party_app_serves_a_game(tmp_path):
    cp = write_fixture_checkpoint(tmp_path)
    beerpong.play("fixture-brain-v1", cp, tmp_path / "g", run_id="party-test", log=lambda *_: None)
    server = serve(tmp_path / "g", port=0, block=False, app="party")
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        status, body = get(base + "/")
        assert status == 200 and b"FLYPONG" in body and b"party.js" in body
        assert get(base + "/static/party/party.css")[0] == 200
        assert get(base + "/static/flylib.js")[0] == 200
        idx = json.loads(get(base + "/api/index")[1])
        kinds = [e["kind"] for e in idx["chain"]]
        assert kinds[0] == "pong_header" and kinds[1] == "calibration" and kinds[-1] == "pong_result"
        try:
            get(base + "/choose")
            assert False, "lab pages must not be served by the party app"
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        server.shutdown()
        server.server_close()
