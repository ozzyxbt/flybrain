import json
import urllib.request

from flybrain.dashboard import serve


def get(url):
    with urllib.request.urlopen(url) as r:
        return r.status, r.read()


def test_dashboard_serves_pages_and_chain_derived_api(small_run):
    out, summary = small_run
    server = serve(out, port=0, block=False)
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        for page in ["/choose", "/coin", "/brain", "/"]:
            status, body = get(base + page)
            assert status == 200 and b"FLYBRAIN" in body
        status, body = get(base + "/api/index")
        idx = json.loads(body)
        assert idx["chain_error"] is None and idx["chain"][-1]["sha256"] == summary["chain_head"]
        assert idx["manifest_sha256"] == summary["manifest_sha256"]
        assert json.loads(get(base + "/api/verify")[1])["ok"]
        assert json.loads(get(base + "/api/brain")[1])["sources"]["edges.feather"]["bytes"] == 1051241946
        status, body = get(base + "/run/chain.jsonl")
        assert status == 200 and body == (out / "chain.jsonl").read_bytes()
        assert get(base + "/api/bundle.zip")[1][:2] == b"PK"
        try:
            get(base + "/run/../pyproject.toml")
            assert False, "path escape served"
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        server.shutdown()
        server.server_close()
