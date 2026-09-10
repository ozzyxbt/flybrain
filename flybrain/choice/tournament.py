"""Bias-resistant visual tournament over the precommitted manifest.

Bracket: candidates are paired in manifest order (1v2, 3v4, ...); an odd
candidate receives a bye to the next round. Every match is decided by the
fixed decoder over mirrored trials, restarting from the frozen checkpoint.
Attempts within a match use the predeclared presentation variants in order.
After the last attempt without a decision the match, and therefore the
category, is ``NO_DECISION``. Nobody picks.

Launch timing: ``launch_action`` is run as up to ``max_windows`` windows. A
``wait`` or ``NO_DECISION`` window schedules the next; no decisive ``launch``
within the published windows ends the experiment without a token.
"""

from .. import PROTOCOL
from . import decoder, renderer
from .manifest import CATEGORIES, candidates

IDENTITY = ("name", "ticker", "logo", "palette", "description")


def trial_key(category, rnd, match, attempt, trial):
    return f"{category}-r{rnd}-m{match}-a{attempt}-t{trial}"


class Tournament:
    def __init__(self, manifest, manifest_sha256, brain, transcript, log=print):
        self.m = manifest
        self.msha = manifest_sha256
        self.brain = brain
        self.t = transcript
        self.log = log
        self.window_ms = manifest["neural_window_ms"]
        self.threshold = manifest["decoder_threshold_hz"]

    # -- trial -------------------------------------------------------------
    def trial(self, category, rnd, match, attempt, trial_no, left, right, variant, header_extra=""):
        key = trial_key(category, rnd, match, attempt, trial_no)
        frame = renderer.render(self.m, category, left, right, variant, header_extra)
        counts, neural_time = self.brain.evaluate(frame, self.window_ms)
        saved = self.t.save_trial_inputs(key, frame, counts)
        read = decoder.readout(counts, self.brain.cells, self.window_ms)
        envelope = {
            "protocol": PROTOCOL,
            "run_id": self.t.run_id,
            "manifest_sha256": self.msha,
            "category": category,
            "round": rnd,
            "match": match,
            "attempt": attempt,
            "trial": trial_no,
            "variant": variant,
            "header_extra": header_extra,
            "left_candidate_id": left["id"],
            "right_candidate_id": right["id"],
            "input_sha256": saved["input_sha256"],
            "spike_sha256": saved["spike_sha256"],
            "frame_path": saved["frame_path"],
            "spike_path": saved["spike_path"],
            "checkpoint_sha256": self.brain.checkpoint_sha256,
            "backend": self.brain.model,
            "left_hz": read["left_hz"],
            "right_hz": read["right_hz"],
            "gate_spikes": read["gate_spikes"],
            "result": read["raw_side"],
            "neural_window_ms": self.window_ms,
            "neural_time_ms": neural_time,
            "decoder_cells": self.brain.cell_ids,
            "learning_frozen": True,
            "reinforcement": "none",
        }
        sha = self.t.add("trial", f"trials/{key}.json", envelope)
        self.log(
            f"  trial {key}: L={read['left_hz']} R={read['right_hz']} gate={read['gate_spikes']} "
            f"[{left['id']} | {right['id']}] -> {read['raw_side']}"
        )
        return envelope, sha

    # -- attempt / match ---------------------------------------------------
    def attempt(self, category, rnd, match, attempt_no, a, b, header_extra=""):
        variant = self.m["attempt_variants"][attempt_no - 1]
        t1, s1 = self.trial(category, rnd, match, attempt_no, 1, a, b, variant, header_extra)
        t2, s2 = self.trial(category, rnd, match, attempt_no, 2, b, a, variant, header_extra)
        sc = decoder.score(t1, t2, self.threshold)
        return {
            "attempt": attempt_no,
            "variant": variant,
            "trial_1_sha256": s1,
            "trial_2_sha256": s2,
            "trial_1": {k: t1[k] for k in ["left_candidate_id", "right_candidate_id", "left_hz", "right_hz", "gate_spikes"]},
            "trial_2": {k: t2[k] for k in ["left_candidate_id", "right_candidate_id", "left_hz", "right_hz", "gate_spikes"]},
            "a_score": sc["a_score"],
            "b_score": sc["b_score"],
            "result": sc["result"],
        }

    def match(self, category, rnd, match_no, a, b, header_extra=""):
        self.log(f"match {category} r{rnd} m{match_no}: {a['id']} vs {b['id']}")
        attempts = []
        winner = None
        for n in range(1, self.m["max_attempts_per_match"] + 1):
            att = self.attempt(category, rnd, match_no, n, a, b, header_extra)
            attempts.append(att)
            if att["result"] == "A":
                winner = a["id"]
                break
            if att["result"] == "B":
                winner = b["id"]
                break
        artifact = {
            "protocol": PROTOCOL,
            "run_id": self.t.run_id,
            "manifest_sha256": self.msha,
            "category": category,
            "round": rnd,
            "match": match_no,
            "header_extra": header_extra,
            "candidate_a": a["id"],
            "candidate_b": b["id"],
            "threshold_hz": self.threshold,
            "max_attempts": self.m["max_attempts_per_match"],
            "attempts": attempts,
            "winner": winner,
            "result": winner if winner else "NO_DECISION",
        }
        sha = self.t.add("match_result", f"matches/{category}-r{rnd}-m{match_no}.json", artifact)
        self.log(f"  -> {artifact['result']} after {len(attempts)} attempt(s)")
        return artifact, sha

    # -- category ----------------------------------------------------------
    def category(self, category):
        pool = candidates(self.m, category)
        bracket = []
        rnd = 1
        winner = None
        no_decision = False
        while len(pool) > 1 and not no_decision:
            matches = []
            nxt = []
            for i in range(0, len(pool) - 1, 2):
                a, b = pool[i], pool[i + 1]
                art, sha = self.match(category, rnd, len(matches) + 1, a, b)
                matches.append({"match": len(matches) + 1, "a": a["id"], "b": b["id"], "winner": art["winner"], "sha256": sha})
                if art["winner"] is None:
                    no_decision = True
                    break
                nxt.append(a if art["winner"] == a["id"] else b)
            byes = [pool[-1]["id"]] if len(pool) % 2 else []
            if byes:
                nxt.append(pool[-1])
            bracket.append({"round": rnd, "matches": matches, "byes": byes})
            pool = nxt
            rnd += 1
        if not no_decision:
            winner = pool[0]["id"]
        artifact = {
            "protocol": PROTOCOL,
            "run_id": self.t.run_id,
            "manifest_sha256": self.msha,
            "category": category,
            "bracket": bracket,
            "winner": winner,
            "result": winner if winner else "NO_DECISION",
        }
        sha = self.t.add("category_result", f"categories/{category}.json", artifact)
        self.t.committer.commit("category_root", sha, category)
        self.log(f"category {category}: {artifact['result']}")
        return artifact, sha

    # -- launch windows ----------------------------------------------------
    def launch_windows(self):
        launch, wait = candidates(self.m, "launch_action")
        assert launch["id"] == "launch" and wait["id"] == "wait"
        cfg = self.m["launch_windows"]
        windows = []
        outcome = "NO_LAUNCH"
        for w in range(1, cfg["max_windows"] + 1):
            extra = f"WINDOW {w}/{cfg['max_windows']}"
            art, sha = self.match("launch_action", w, 1, launch, wait, extra)
            record = {"window": w, "match_sha256": sha, "result": art["result"]}
            if art["result"] == "launch":
                outcome = "LAUNCH"
                windows.append(record)
                break
            record["next_window_after_seconds"] = cfg["interval_seconds"] if w < cfg["max_windows"] else None
            windows.append(record)
        artifact = {
            "protocol": PROTOCOL,
            "run_id": self.t.run_id,
            "manifest_sha256": self.msha,
            "category": "launch_action",
            "max_windows": cfg["max_windows"],
            "interval_seconds": cfg["interval_seconds"],
            "windows": windows,
            "winner": "launch" if outcome == "LAUNCH" else None,
            "result": outcome,
        }
        sha = self.t.add("category_result", "categories/launch_action.json", artifact)
        self.t.committer.commit("category_root", sha, "launch_action")
        self.log(f"launch windows: {outcome}")
        return artifact, sha

    # -- whole run ---------------------------------------------------------
    def run(self):
        results = {}
        roots = {}
        for cat in IDENTITY:
            art, sha = self.category(cat)
            results[cat] = art["winner"]
            roots[cat] = sha
        identity_complete = all(results[c] is not None for c in IDENTITY)
        skipped = []
        if identity_complete:
            art, sha = self.category("launch_venue")
            results["launch_venue"] = art["winner"]
            roots["launch_venue"] = sha
            art, sha = self.launch_windows()
            results["launch_action"] = art["winner"]
            roots["launch_action"] = sha
            outcome = art["result"] if results["launch_venue"] is not None else "NO_LAUNCH"
            reason = None if outcome == "LAUNCH" else ("venue NO_DECISION" if results["launch_venue"] is None else "no decisive launch within published windows")
        else:
            skipped = ["launch_venue", "launch_action"]
            results["launch_venue"] = None
            results["launch_action"] = None
            outcome = "NO_LAUNCH"
            reason = "identity incomplete: " + ", ".join(c for c in IDENTITY if results[c] is None)
        final = {
            "protocol": PROTOCOL,
            "run_id": self.t.run_id,
            "manifest_sha256": self.msha,
            "checkpoint_sha256": self.brain.checkpoint_sha256,
            "backend": self.brain.model,
            "identity": {c: results[c] for c in IDENTITY},
            "identity_complete": identity_complete,
            "launch_venue": results["launch_venue"],
            "venue_selection_mode": self.m["venue_selection_mode"],
            "launch_action": results["launch_action"],
            "skipped_categories": skipped,
            "category_roots": roots,
            "outcome": outcome,
            "reason": reason,
            "disclosure": self.m["disclosure"],
            "category_order": list(CATEGORIES),
        }
        sha = self.t.add("final_decision", "final/decision.json", final)
        self.t.committer.commit("final_decision", sha)
        self.log(f"final decision {sha[:16]}: {outcome}" + (f" ({reason})" if reason else ""))
        return final, sha
