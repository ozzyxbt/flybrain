"""flybrain command line. Development default: fixture backend, mock launch."""

import argparse
import json
import sys
from pathlib import Path


def main(argv=None):
    p = argparse.ArgumentParser(prog="flybrain")
    sub = p.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run the full choice tournament and mock launch")
    run.add_argument("--manifest", type=Path, default=Path("manifests/genesis-v1.json"))
    run.add_argument("--checkpoint", type=Path, default=Path("manifests/fixture-checkpoint-v1.json"))
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--run-id")
    run.add_argument("--quiet", action="store_true")

    ver = sub.add_parser("verify-run", help="Recompute every hash and rule in a run directory")
    ver.add_argument("run_dir", type=Path)
    ver.add_argument("--resimulate", action="store_true", help="Fixture backend only: rerun the model and compare spikes")
    ver.add_argument("--json", action="store_true")

    serve = sub.add_parser("serve", help="Serve the /choose, /coin and /brain dashboard for a run")
    serve.add_argument("--run", type=Path, required=True)
    serve.add_argument("--port", type=int, default=8787)
    serve.add_argument("--host", default="127.0.0.1")

    render = sub.add_parser("render", help="Render one choice frame to PNG")
    render.add_argument("--manifest", type=Path, default=Path("manifests/genesis-v1.json"))
    render.add_argument("--category", required=True)
    render.add_argument("--left", required=True)
    render.add_argument("--right", required=True)
    render.add_argument("--variant", default="standard")
    render.add_argument("--out", type=Path, required=True)

    mh = sub.add_parser("manifest-hash", help="Validate a manifest and print its canonical SHA-256")
    mh.add_argument("manifest", type=Path)

    mc = sub.add_parser("manifest-canonicalize", help="Validate a draft manifest and write canonical bytes")
    mc.add_argument("draft", type=Path)
    mc.add_argument("out", type=Path)
    mc.add_argument("--checkpoint", type=Path, help="Fill brain_checkpoint_sha256 from this file")

    pp = sub.add_parser("pons-preview", help="Build and inspect the unsigned pons v2 launchToken call for a run's final decision; never submits")
    pp.add_argument("--run", type=Path, required=True)
    pp.add_argument("--rpc", help="Read-only JSON-RPC for chain id, launchFee() and the economics pin (optional)")
    pp.add_argument("--creator-fee-recipient", help="Disclosed treasury address that receives pons creator fees")
    pp.add_argument("--launch-config-id", type=int, default=0)
    pp.add_argument("--logo-uri", help="Hosted logo URL for the token's logo() field")
    pp.add_argument("--out", type=Path)

    pong = sub.add_parser("pong", help="Game mode: the fly plays beer pong (hash-chained record, not the choice protocol)")
    pong.add_argument("--backend", choices=["fixture-brain-v1", "malecns-connectome"], default="fixture-brain-v1")
    pong.add_argument("--checkpoint", type=Path, default=Path("manifests/fixture-checkpoint-v1.json"))
    pong.add_argument("--out", type=Path, required=True)
    pong.add_argument("--run-id")
    pong.add_argument("--throws", type=int)
    pong.add_argument("--quiet", action="store_true")

    sub.add_parser("prepare", help="Download and compile MaleCNS v1.0 (about 1.1 GB; connectome backend only)")
    sub.add_parser("verify-data", help="Verify the prepared connectome dataset")
    ck = sub.add_parser("checkpoint", help="Create the frozen genesis checkpoint for the connectome backend")
    ck.add_argument("--out", type=Path, default=Path("data/checkpoints/genesis.npz"))

    a = p.parse_args(argv)

    if a.command == "run":
        from .run import run as run_fn

        log = (lambda *_: None) if a.quiet else print
        summary = run_fn(a.manifest, a.checkpoint, a.out, a.run_id, log=log)
        print(json.dumps(summary, indent=2))
        return 0
    if a.command == "verify-run":
        from .verifier.verify import verify_run

        report = verify_run(a.run_dir, resimulate=a.resimulate)
        if a.json:
            print(json.dumps(report, indent=2))
        else:
            for c in report["checks"]:
                if not c["ok"]:
                    print(f"FAIL  {c['check']}  {c['detail']}")
                elif c.get("warning"):
                    print(f"WARN  {c['check']}  {c['detail']}")
            print(f"{'OK' if report['ok'] else 'FAILED'}: {len(report['checks'])} checks, {report['failures']} failures, {report['warnings']} warnings")
        return 0 if report["ok"] else 1
    if a.command == "serve":
        from .dashboard import serve as serve_fn

        serve_fn(a.run, a.host, a.port)
        return 0
    if a.command == "render":
        from .choice import manifest as mm
        from .choice import renderer

        m, _ = mm.load(a.manifest)
        frame = renderer.render(m, a.category, mm.candidate(m, a.category, a.left), mm.candidate(m, a.category, a.right), a.variant)
        renderer.save_png(frame, a.out)
        print(a.out)
        return 0
    if a.command == "manifest-hash":
        from .choice import manifest as mm

        _, digest = mm.load(a.manifest)
        print(digest)
        return 0
    if a.command == "manifest-canonicalize":
        from .choice import manifest as mm
        from .commitments.canonical import file_sha256, write_canonical

        draft = json.loads(a.draft.read_text())
        if a.checkpoint:
            draft["brain_checkpoint_sha256"] = file_sha256(a.checkpoint)
        mm.validate(draft)
        print(write_canonical(a.out, draft))
        return 0
    if a.command == "pong":
        from .games.beerpong import play

        summary = play(a.backend, a.checkpoint, a.out, a.run_id, a.throws, log=(lambda *_: None) if a.quiet else print)
        print(json.dumps(summary, indent=2))
        return 0
    if a.command == "pons-preview":
        from .commitments.canonical import load_canonical
        from .launch.base import build_intent
        from .launch.pons import NETWORK, PonsAdapter
        from .risk.policy import LaunchSettings

        final, final_sha = load_canonical(a.run / "final" / "decision.json")
        manifest, _ = load_canonical(a.run / "manifest.json")
        if final["outcome"] != "LAUNCH" or final["launch_venue"] != "pons":
            raise SystemExit(f"Run's final decision is {final['outcome']} with venue {final['launch_venue']}; pons preview only applies to a LAUNCH on pons")
        logo = a.run / "final" / "logo.png"
        from .choice.renderer import load_png
        from .commitments.canonical import sha256_hex

        logo_sha = sha256_hex(load_png(logo).tobytes()) if logo.exists() else "0" * 64
        settings = LaunchSettings(network=NETWORK, allowed_networks=())
        intent = build_intent(final, final_sha, manifest, final["run_id"], settings, logo_sha)
        adapter = PonsAdapter(a.run / "launch" / "pons-ledger", rpc=a.rpc, creator_fee_recipient=a.creator_fee_recipient, launch_config_id=a.launch_config_id, logo_uri=a.logo_uri)
        pre = adapter.preflight(intent)
        unsigned = adapter.build_unsigned(intent)
        export = adapter.export(intent, unsigned, pre)
        out = a.out or (a.run / "launch" / "pons-preview.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(export, indent=2) + "\n")
        print(json.dumps({"written": str(out), "preflight_ok": pre.ok, "inspection_problems": export["inspection"], "selector": unsigned.instructions[0]["data"]["tx"]["selector"], "calldata_sha256": unsigned.payload_sha256, "salt": unsigned.instructions[0]["data"]["salt"]}, indent=2))
        return 0 if pre.ok and not export["inspection"] else 1
    if a.command in ("prepare", "verify-data"):
        from .neural.data import prepare, verify

        if a.command == "prepare":
            prepare()
        else:
            print(json.dumps(verify()))
        return 0
    if a.command == "checkpoint":
        from .choice.backends import ConnectomeBrain

        a.out.parent.mkdir(parents=True, exist_ok=True)
        if a.out.exists():
            raise SystemExit("Checkpoint exists; a published checkpoint is never overwritten")
        b = ConnectomeBrain(a.out)
        print(json.dumps({"checkpoint": str(a.out), "sha256": b.checkpoint_sha256, "cells": b.cell_ids}, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
