"""Public dashboard served straight from the hash-chained run directory.

There is no database. ``/api/index`` walks ``chain.jsonl``, verifying every
link and hash as it goes, and returns the artifacts verbatim; the pages render
those. ``/api/verify`` runs the full verifier on demand.
"""

import json
import mimetypes
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .commitments.hashchain import walk
from .commitments.solana_memo import read_commitments

WEB = Path(__file__).with_name("web")
PAGES = {"/": "choose.html", "/choose": "choose.html", "/coin": "coin.html", "/brain": "brain.html"}


def index(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    entries = []
    error = None
    try:
        for entry, artifact, digest in walk(run_dir):
            entries.append({**entry, "artifact": artifact})
    except ValueError as e:
        error = str(e)
    manifest = json.loads((run_dir / "manifest.json").read_text()) if (run_dir / "manifest.json").exists() else None
    meta = json.loads((run_dir / "run-meta.json").read_text()) if (run_dir / "run-meta.json").exists() else {}
    return {
        "manifest": manifest,
        "manifest_sha256": (run_dir / "manifest.sha256").read_text().strip() if (run_dir / "manifest.sha256").exists() else None,
        "chain": entries,
        "chain_error": error,
        "commitments": read_commitments(run_dir),
        "meta": meta,
        "stop": (run_dir / "STOP").read_text() if (run_dir / "STOP").exists() else None,
    }


def brain_info() -> dict:
    from . import BASELINE_COMMIT

    neural = Path(__file__).with_name("neural")
    return {
        "baseline_commit": BASELINE_COMMIT,
        "datasets": json.loads((neural / "datasets.json").read_text())["datasets"],
        "sources": json.loads((neural / "sources.lock.json").read_text()),
        "arrays": json.loads((neural / "arrays.lock.json").read_text()),
    }


def bundle(run_dir: Path) -> bytes:
    """Zip of the run directory: everything a verifier needs, nothing else."""
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(run_dir.rglob("*")):
            if p.is_file() and "mock-ledger" not in p.parts:
                z.write(p, str(p.relative_to(run_dir)))
    return buf.getvalue()


def make_handler(run_dir: Path):
    run_dir = Path(run_dir).resolve()

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def _send(self, status, body: bytes, ctype: str):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path in PAGES:
                return self._send(200, (WEB / PAGES[path]).read_bytes(), "text/html; charset=utf-8")
            if path == "/api/index":
                return self._send(200, json.dumps(index(run_dir)).encode(), "application/json")
            if path == "/api/verify":
                from .verifier.verify import verify_run

                return self._send(200, json.dumps(verify_run(run_dir)).encode(), "application/json")
            if path == "/api/brain":
                return self._send(200, json.dumps(brain_info()).encode(), "application/json")
            if path == "/api/bundle.zip":
                return self._send(200, bundle(run_dir), "application/zip")
            if path.startswith("/static/"):
                target = (WEB / path[len("/static/") :]).resolve()
                if target.is_file() and target.is_relative_to(WEB):
                    return self._send(200, target.read_bytes(), mimetypes.guess_type(str(target))[0] or "application/octet-stream")
            if path.startswith("/run/"):
                target = (run_dir / path[len("/run/") :]).resolve()
                if target.is_file() and target.is_relative_to(run_dir):
                    return self._send(200, target.read_bytes(), mimetypes.guess_type(str(target))[0] or "application/octet-stream")
            return self._send(404, b"not found", "text/plain")

    return Handler


def serve(run_dir, host="127.0.0.1", port=8787, block=True):
    server = ThreadingHTTPServer((host, port), make_handler(run_dir))
    print(f"flybrain dashboard: http://{host}:{server.server_address[1]}/choose  (run: {run_dir})", flush=True)
    if block:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return None
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
