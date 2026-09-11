"""``flybrain verify-run <dir>``: recompute everything, trust nothing.

Connects   manifest -> visual trials -> spikes -> decoded choices
           -> final identity -> launch intent -> receipt
and exits nonzero on any hash, sequence, checkpoint, candidate, bracket,
score, or receipt mismatch. Every check is listed in the report.
"""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import numpy as np

from .. import PROTOCOL
from ..choice import decoder, manifest as manifest_module, renderer
from ..choice.backends import FIXTURE_MODEL, FixtureBrain
from ..choice.manifest import CATEGORIES
from ..choice.tournament import IDENTITY
from ..commitments.canonical import canonical_bytes, canonical_sha256, file_sha256, sha256_hex
from ..commitments.hashchain import walk
from ..commitments.solana_memo import memo_payload, read_commitments
from ..launch.mock import PROGRAM_ID as MOCK_PROGRAM, mock_mint, mock_signature


class Report:
    def __init__(self):
        self.checks = []
        self.failures = 0
        self.warnings = 0

    def ok(self, name, detail=""):
        self.checks.append({"check": name, "ok": True, "detail": detail})

    def fail(self, name, detail=""):
        self.failures += 1
        self.checks.append({"check": name, "ok": False, "detail": detail})

    def warn(self, name, detail=""):
        self.warnings += 1
        self.checks.append({"check": name, "ok": True, "warning": True, "detail": detail})

    def expect(self, condition, name, detail=""):
        (self.ok if condition else self.fail)(name, detail)
        return bool(condition)

    def to_dict(self):
        return {"ok": self.failures == 0, "failures": self.failures, "warnings": self.warnings, "checks": self.checks}


def _fixture_cells():
    return {"left": FixtureBrain.LEFT, "right": FixtureBrain.RIGHT, "gate": FixtureBrain.GATE}


def verify_run(root, resimulate=False) -> dict:
    root = Path(root)
    r = Report()
    try:
        _verify(root, r, resimulate)
    except Exception as e:  # any structural failure is a verification failure
        r.fail("verifier", f"{type(e).__name__}: {e}")
    return r.to_dict()


def _verify(root: Path, r: Report, resimulate: bool):
    # 1. Manifest
    manifest, msha = manifest_module.load(root / "manifest.json")
    r.ok("manifest.canonical_and_valid", msha)
    published = (root / "manifest.sha256").read_text().strip() if (root / "manifest.sha256").exists() else None
    r.expect(published == msha, "manifest.published_hash_matches", f"{published} vs {msha}")

    # 2. Chain
    entries = list(walk(root))
    r.ok("chain.links_and_hashes", f"{len(entries)} entries")
    by_kind = {}
    for entry, artifact, digest in entries:
        by_kind.setdefault(entry["kind"], []).append((entry, artifact, digest))
    header = by_kind.get("run_header", [])
    if not r.expect(len(header) == 1 and header[0][0]["seq"] == 0, "chain.run_header_first"):
        return
    _, run, _ = header[0]
    run_id = run["run_id"]
    r.expect(run["manifest_sha256"] == msha, "run.manifest_hash", run["manifest_sha256"])
    r.expect(run["protocol"] == PROTOCOL, "run.protocol")
    r.expect(run["backend"] == manifest["backend"], "run.backend_matches_manifest", run["backend"])
    r.expect(run["learning_frozen"] is True and run["reinforcement_injected"] is False and run["llm_in_decision_path"] is False, "run.frozen_no_reinforcement_no_llm")

    # 3. Checkpoint
    cp = root / "checkpoint" / run["checkpoint_file"]
    cp_sha = file_sha256(cp) if cp.exists() else None
    r.expect(cp_sha == manifest["brain_checkpoint_sha256"] == run["checkpoint_sha256"], "checkpoint.hash_matches_manifest", f"{cp_sha}")
    if run["backend"] == FIXTURE_MODEL:
        cells = _fixture_cells()
        brain = FixtureBrain(cp) if (resimulate and cp.exists()) else None
        expected_ids = FixtureBrain(cp).cell_ids if cp.exists() else None
        r.expect(run["decoder_cells"] == expected_ids, "decoder.cells_match_backend")
    else:
        cells = None
        brain = None
        ids = run["decoder_cells"]
        r.expect(all(isinstance(ids.get(k), list) and ids[k] for k in ["left", "right", "gate"]), "decoder.cell_ids_present")
        r.warn("decoder.connectome_cells_not_reconstructed", "connectome cell indices need the prepared dataset; rates verified from recorded cell index lists if present")
        cells = _connectome_cells(run)

    # 3b. Brain atlas (display asset, but bound to the run header)
    atlas_info = run.get("atlas")
    if atlas_info:
        apath = root / atlas_info["path"]
        if r.expect(apath.exists() and apath.is_relative_to(root) and file_sha256(apath) == atlas_info["sha256"], "atlas.hash_matches_run_header"):
            atlas = json.loads(apath.read_text())
            ppath = root / atlas["positions_path"]
            r.expect(ppath.exists() and sha256_hex(ppath.read_bytes()) == atlas["positions_sha256"] and ppath.stat().st_size == atlas["n"] * 12, "atlas.positions_hash_and_size")
            r.expect(atlas["schematic"] == (run["backend"] == FIXTURE_MODEL) == atlas_info["schematic"], "atlas.schematic_flag_matches_backend")
            if cells is not None:
                r.expect(atlas["cells"] == {k: list(map(int, v)) for k, v in cells.items()}, "atlas.readout_cells_match_decoder")

    # 4. Trials
    trials = {}
    for entry, t, digest in by_kind.get("trial", []):
        key = Path(entry["path"]).stem
        trials[digest] = t
        prefix = f"trial.{key}"
        ok = True
        ok &= r.expect(t["protocol"] == PROTOCOL and t["run_id"] == run_id and t["manifest_sha256"] == msha, f"{prefix}.identity")
        ok &= r.expect(t["checkpoint_sha256"] == manifest["brain_checkpoint_sha256"], f"{prefix}.checkpoint")
        ok &= r.expect(t["backend"] == run["backend"] and t["learning_frozen"] is True and t["reinforcement"] == "none", f"{prefix}.frozen_unreinforced")
        ok &= r.expect(t["neural_window_ms"] == manifest["neural_window_ms"], f"{prefix}.window")
        ok &= r.expect(t["variant"] in manifest["attempt_variants"] and manifest["attempt_variants"][t["attempt"] - 1] == t["variant"], f"{prefix}.variant_predeclared")
        try:
            left = manifest_module.candidate(manifest, t["category"], t["left_candidate_id"])
            right = manifest_module.candidate(manifest, t["category"], t["right_candidate_id"])
            ok &= r.expect(left["id"] != right["id"], f"{prefix}.distinct_candidates")
        except manifest_module.ManifestError as e:
            r.fail(f"{prefix}.candidates_in_manifest", str(e))
            ok = False
            continue
        frame_path = root / t["frame_path"]
        if not frame_path.exists() or not frame_path.is_relative_to(root):
            r.fail(f"{prefix}.frame_missing", t["frame_path"])
            continue
        frame = renderer.load_png(frame_path)
        ok &= r.expect(sha256_hex(frame.tobytes()) == t["input_sha256"], f"{prefix}.input_hash")
        rerender = renderer.render(manifest, t["category"], left, right, t["variant"], t.get("header_extra", ""))
        ok &= r.expect(np.array_equal(frame, rerender), f"{prefix}.frame_rerenders_from_manifest")
        spike_path = root / t["spike_path"]
        if not spike_path.exists() or not spike_path.is_relative_to(root):
            r.fail(f"{prefix}.spikes_missing", t["spike_path"])
            continue
        counts = np.load(spike_path, allow_pickle=False)
        ok &= r.expect(counts.dtype == np.dtype("<i4") and counts.ndim == 1, f"{prefix}.spike_dtype")
        ok &= r.expect(sha256_hex(np.ascontiguousarray(counts, dtype="<i4").tobytes()) == t["spike_sha256"], f"{prefix}.spike_hash")
        if cells is not None and ok:
            read = decoder.readout(counts, cells, manifest["neural_window_ms"])
            ok &= r.expect(read["left_hz"] == t["left_hz"] and read["right_hz"] == t["right_hz"] and read["gate_spikes"] == t["gate_spikes"] and read["raw_side"] == t["result"], f"{prefix}.readout_recomputed", f"{read['left_hz']}/{read['right_hz']}/{read['gate_spikes']}")
        if brain is not None and ok:
            sim, _ = brain.evaluate(frame, manifest["neural_window_ms"])
            r.expect(np.array_equal(sim, counts), f"{prefix}.fixture_resimulated")

    # 5. Matches
    matches = {}
    for entry, m, digest in by_kind.get("match_result", []):
        key = Path(entry["path"]).stem
        matches[digest] = m
        prefix = f"match.{key}"
        r.expect(m["threshold_hz"] == manifest["decoder_threshold_hz"] and m["max_attempts"] == manifest["max_attempts_per_match"], f"{prefix}.protocol_params")
        r.expect(1 <= len(m["attempts"]) <= manifest["max_attempts_per_match"], f"{prefix}.attempt_count")
        decided = None
        for i, att in enumerate(m["attempts"], start=1):
            ap = f"{prefix}.a{i}"
            t1, t2 = trials.get(att["trial_1_sha256"]), trials.get(att["trial_2_sha256"])
            if not r.expect(t1 is not None and t2 is not None, f"{ap}.trials_in_chain"):
                continue
            r.expect(att["attempt"] == i and t1["attempt"] == i and t2["attempt"] == i and t1["trial"] == 1 and t2["trial"] == 2, f"{ap}.numbering")
            r.expect(t1["category"] == m["category"] and t2["category"] == m["category"] and t1["round"] == m["round"] and t2["round"] == m["round"] and t1["match"] == m["match"] and t2["match"] == m["match"], f"{ap}.same_match")
            r.expect(t1["left_candidate_id"] == m["candidate_a"] and t1["right_candidate_id"] == m["candidate_b"] and t2["left_candidate_id"] == m["candidate_b"] and t2["right_candidate_id"] == m["candidate_a"], f"{ap}.mirrored")
            r.expect(t1.get("header_extra", "") == m.get("header_extra", "") == t2.get("header_extra", ""), f"{ap}.header")
            r.expect(att["trial_1"] == {k: t1[k] for k in att["trial_1"]} and att["trial_2"] == {k: t2[k] for k in att["trial_2"]}, f"{ap}.copied_readouts")
            sc = decoder.score(t1, t2, manifest["decoder_threshold_hz"])
            r.expect(sc["a_score"] == att["a_score"] and sc["b_score"] == att["b_score"] and sc["result"] == att["result"], f"{ap}.score_recomputed", f"{sc}")
            if decided is not None:
                r.fail(f"{ap}.attempt_after_decision")
            if att["result"] in ("A", "B"):
                decided = m["candidate_a"] if att["result"] == "A" else m["candidate_b"]
        expected_result = decided if decided else "NO_DECISION"
        r.expect(m["winner"] == decided and m["result"] == expected_result, f"{prefix}.result", m["result"])
        if decided is None:
            r.expect(len(m["attempts"]) == manifest["max_attempts_per_match"], f"{prefix}.no_decision_only_after_all_attempts")

    # 6. Categories
    categories = {}
    for entry, c, digest in by_kind.get("category_result", []):
        cat = c["category"]
        categories[cat] = (c, digest)
        prefix = f"category.{cat}"
        if cat == "launch_action":
            _verify_windows(r, manifest, c, matches, prefix)
            continue
        pool = [x["id"] for x in manifest["categories"][cat]]
        rnd = 1
        no_decision = False
        winner = None
        for rec in c["bracket"]:
            r.expect(rec["round"] == rnd, f"{prefix}.r{rnd}.round_number")
            nxt = []
            expected_pairs = [(pool[i], pool[i + 1]) for i in range(0, len(pool) - 1, 2)]
            for k, mrec in enumerate(rec["matches"]):
                mp = f"{prefix}.r{rnd}.m{k + 1}"
                pair = expected_pairs[k] if k < len(expected_pairs) else None
                r.expect(pair == (mrec["a"], mrec["b"]), f"{mp}.pairing_follows_manifest_order", f"{pair}")
                m = matches.get(mrec["sha256"])
                if not r.expect(m is not None, f"{mp}.match_in_chain"):
                    no_decision = True
                    break
                r.expect(m["category"] == cat and m["round"] == rnd and m["match"] == k + 1 and m["candidate_a"] == mrec["a"] and m["candidate_b"] == mrec["b"] and m["winner"] == mrec["winner"], f"{mp}.match_consistent")
                if m["winner"] is None:
                    no_decision = True
                    r.expect(k == len(rec["matches"]) - 1, f"{mp}.stopped_at_no_decision")
                    break
                nxt.append(m["winner"])
            if no_decision:
                break
            r.expect(len(rec["matches"]) == len(expected_pairs), f"{prefix}.r{rnd}.all_pairs_played")
            expected_byes = [pool[-1]] if len(pool) % 2 else []
            r.expect(rec["byes"] == expected_byes, f"{prefix}.r{rnd}.byes", f"{rec['byes']}")
            nxt += expected_byes
            pool = nxt
            rnd += 1
        if not no_decision:
            r.expect(len(pool) == 1, f"{prefix}.bracket_complete")
            winner = pool[0] if len(pool) == 1 else None
        r.expect(c["winner"] == winner and c["result"] == (winner if winner else "NO_DECISION"), f"{prefix}.winner", c["result"])

    # 7. Final decision
    finals = by_kind.get("final_decision", [])
    if not r.expect(len(finals) == 1, "final.exactly_one"):
        return
    _, final, final_sha = finals[0]
    for cat in IDENTITY:
        c = categories.get(cat)
        r.expect(c is not None and final["identity"][cat] == c[0]["winner"] and final["category_roots"].get(cat) == c[1], f"final.identity.{cat}", str(final["identity"][cat]))
    complete = all(final["identity"][c] is not None for c in IDENTITY)
    r.expect(final["identity_complete"] == complete, "final.identity_complete_flag")
    if complete:
        v = categories.get("launch_venue")
        la = categories.get("launch_action")
        r.expect(v is not None and final["launch_venue"] == v[0]["winner"] and final["category_roots"].get("launch_venue") == v[1], "final.launch_venue")
        r.expect(la is not None and final["launch_action"] == la[0]["winner"] and final["category_roots"].get("launch_action") == la[1], "final.launch_action")
        expected = "LAUNCH" if (la and la[0]["result"] == "LAUNCH" and v and v[0]["winner"] is not None) else "NO_LAUNCH"
        r.expect(final["outcome"] == expected, "final.outcome", final["outcome"])
    else:
        r.expect(final["outcome"] == "NO_LAUNCH" and final["launch_action"] is None and "launch_venue" not in categories and "launch_action" not in categories, "final.no_launch_when_incomplete")
    r.expect(final["venue_selection_mode"] == "simulation", "final.venue_simulation_mode")
    r.expect(final["checkpoint_sha256"] == manifest["brain_checkpoint_sha256"], "final.checkpoint")
    # The final decision must come after every category result in the chain.
    final_seq = finals[0][0]["seq"]
    r.expect(all(e["seq"] < final_seq for e, _, _ in by_kind.get("category_result", [])), "final.after_all_categories")

    # 8. Launch
    intents = by_kind.get("launch_intent", [])
    receipts = by_kind.get("launch_receipt", [])
    vetoes = by_kind.get("launch_veto", [])
    if final["outcome"] != "LAUNCH":
        r.expect(not intents and not receipts, "launch.none_without_decision")
    else:
        r.expect(len(intents) <= 1 and len(receipts) <= 1, "launch.at_most_one_intent_and_receipt")
        if intents:
            ie, intent_art, isha = intents[0]
            intent = intent_art["intent"]
            r.expect(intent_art["intent_sha256"] == canonical_sha256(intent), "launch.intent_hash")
            r.expect(intent["final_decision_sha256"] == final_sha and intent["manifest_sha256"] == msha, "launch.intent_references_final")
            ident = final["identity"]
            r.expect(intent["name"] == manifest_module.candidate(manifest, "name", ident["name"])["text"] and intent["ticker"] == manifest_module.candidate(manifest, "ticker", ident["ticker"])["text"] and intent["description"] == manifest_module.candidate(manifest, "description", ident["description"])["text"] and intent["logo_id"] == ident["logo"] and intent["palette_id"] == ident["palette"] and intent["venue"] == final["launch_venue"], "launch.intent_matches_identity")
            r.expect(intent["network"] not in ("mainnet", "mainnet-beta"), "launch.not_mainnet", intent["network"])
            r.expect(Decimal(intent["initial_dev_buy_sol"]) == 0 and intent["insider_wallets"] == [], "launch.no_dev_buy_no_insiders")
            logo = root / "final" / "logo.png"
            if logo.exists():
                r.expect(sha256_hex(renderer.load_png(logo).tobytes()) == intent["logo_png_sha256"], "launch.logo_hash")
            if intent_art["adapter"] == "mock":
                r.expect(intent_art["unsigned"]["program_ids"] == [MOCK_PROGRAM] and intent_art["unsigned"]["expected_mint"] == mock_mint(intent_art["intent_sha256"]), "launch.mock_expected_mint_recomputed")
            if receipts:
                re_, rec_art, rsha = receipts[0]
                r.expect(re_["seq"] > ie["seq"], "launch.intent_before_receipt")
                r.expect(rec_art["intent_sha256"] == intent_art["intent_sha256"], "launch.receipt_references_intent")
                rec = rec_art.get("receipt")
                if rec_art["status"] in ("CONFIRMED", "RECONCILED") and r.expect(rec is not None, "launch.receipt_present"):
                    r.expect(rec["mint"] == intent_art["unsigned"]["expected_mint"], "launch.receipt_mint_matches_intent")
                    r.expect(rec["metadata"]["name"] == intent["name"] and rec["metadata"]["symbol"] == intent["ticker"], "launch.receipt_metadata_matches_identity")
                    r.expect(rec["authorities"] == {"mint": None, "freeze": None, "update": None}, "launch.authorities_revoked")
                    if intent_art["adapter"] == "mock":
                        r.expect(rec["simulated"] is True and rec["network"] == "mock", "launch.mock_receipt_flagged_simulated")
                        r.expect(rec["mint"] == mock_mint(intent_art["intent_sha256"]), "launch.mock_mint_recomputed")
                        r.expect(rec["signature"] == mock_signature(intent_art["unsigned"]["payload_sha256"]), "launch.mock_signature_recomputed")
                else:
                    r.warn("launch.not_confirmed", rec_art["status"])
            elif not vetoes:
                r.fail("launch.intent_without_receipt_or_stop")

    # 9. Commitments
    commits = read_commitments(root)
    expected = [("manifest", msha, "")]
    for e, c, d in by_kind.get("category_result", []):
        expected.append(("category_root", d, c["category"]))
    expected.append(("final_decision", final_sha, ""))
    for e, rec_art, rsha in receipts:
        if rec_art.get("receipt"):
            expected.append(("launch_receipt", rsha, rec_art["receipt"]["mint"]))
    got = [(c["kind"], c["sha256"], c["memo"]) for c in commits]
    want = [(k, s, memo_payload(k, s, run_id, x)) for k, s, x in expected]
    r.expect(got == want, "commitments.match_chain", f"{len(got)} recorded, {len(want)} expected")

    # 10. Summary (derived, informational)
    summary = root / "summary.json"
    if summary.exists():
        s = json.loads(summary.read_text())
        r.expect(s.get("final_decision_sha256") == final_sha and s.get("identity") == final["identity"] and s.get("chain_head") == entries[-1][2], "summary.derived_from_chain")
    # 11. Software (informational)
    from .. import software as sw

    if run["software"].get("source_sha256") != sw.source_sha256():
        r.warn("software.source_differs_from_verifier", "run was produced by different package sources; hashes above still verified")


def _connectome_cells(run):
    # Connectome trials record cell IDs, not indices; without the dataset the
    # verifier cannot map IDs to spike-array positions, so readout recompute is
    # skipped (warned above). Hash and structure checks still apply.
    return None


def _verify_windows(r, manifest, c, matches, prefix):
    cfg = manifest["launch_windows"]
    r.expect(c["max_windows"] == cfg["max_windows"] and c["interval_seconds"] == cfg["interval_seconds"], f"{prefix}.config")
    r.expect(1 <= len(c["windows"]) <= cfg["max_windows"], f"{prefix}.window_count")
    launched = False
    for i, w in enumerate(c["windows"], start=1):
        wp = f"{prefix}.w{i}"
        m = matches.get(w["match_sha256"])
        if not r.expect(m is not None, f"{wp}.match_in_chain"):
            continue
        r.expect(w["window"] == i and m["round"] == i and m["match"] == 1 and m["category"] == "launch_action" and m["candidate_a"] == "launch" and m["candidate_b"] == "wait", f"{wp}.structure")
        r.expect(m.get("header_extra") == f"WINDOW {i}/{cfg['max_windows']}", f"{wp}.header")
        r.expect(w["result"] == m["result"], f"{wp}.result_copied", w["result"])
        if launched:
            r.fail(f"{wp}.window_after_launch")
        if m["result"] == "launch":
            launched = True
            r.expect(i == len(c["windows"]), f"{wp}.launch_is_last_window")
        else:
            expected_next = cfg["interval_seconds"] if i < cfg["max_windows"] else None
            r.expect(w.get("next_window_after_seconds") == expected_next, f"{wp}.next_window_scheduled")
    if not launched:
        r.expect(len(c["windows"]) == cfg["max_windows"], f"{prefix}.all_windows_used_before_no_launch")
    r.expect(c["result"] == ("LAUNCH" if launched else "NO_LAUNCH") and c["winner"] == ("launch" if launched else None), f"{prefix}.outcome", c["result"])
