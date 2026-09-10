"""Execute a launch from a recorded final decision, durably and at most once.

Order of operations (each step is chained before the next runs):
  1. guard.check_intent  (veto only)
  2. adapter.preflight   (read-only)
  3. build_unsigned + guard.inspect_unsigned
  4. chain `launch_intent` (durable BEFORE any submission)
  5. sign locally, submit
  6. UNKNOWN => halt; reconcile by intent id; never mint twice
  7. chain `launch_receipt`, commit its hash
"""

from ..commitments.canonical import canonical_sha256
from ..risk.policy import Veto


class LaunchHalted(RuntimeError):
    pass


def execute_launch(transcript, intent: dict, final: dict, final_sha256: str, adapter, signer, guard, log=print):
    t = transcript
    guard.check_intent(intent, final, final_sha256)
    pre = adapter.preflight(intent)
    if not pre.ok:
        raise Veto("Preflight failed: " + ", ".join(c["check"] for c in pre.checks if not c["ok"]))
    unsigned = adapter.build_unsigned(intent)
    guard.inspect_unsigned(unsigned.to_dict())
    intent_sha = canonical_sha256(intent)
    t.add(
        "launch_intent",
        "launch/intent.json",
        {
            "protocol": "fly-choice-v1",
            "run_id": t.run_id,
            "intent": intent,
            "intent_sha256": intent_sha,
            "adapter": adapter.name,
            "network": adapter.network,
            "preflight": pre.to_dict(),
            "unsigned": unsigned.to_dict(),
            "status": "PREPARED",
        },
    )
    log(f"launch intent {intent_sha[:16]} persisted; expected mint {unsigned.expected_mint}")
    signed = signer.sign(unsigned)
    result = adapter.submit(signed)
    if result.status == "REJECTED":
        t.add("launch_receipt", "launch/receipt.json", {"protocol": "fly-choice-v1", "run_id": t.run_id, "intent_sha256": intent_sha, "status": "REJECTED", "submission": result.to_dict(), "receipt": None})
        raise LaunchHalted("Submission rejected: " + result.detail)
    if result.status == "UNKNOWN":
        log("submission outcome UNKNOWN; reconciling by intent id, no resubmission")
    receipt = adapter.reconcile(intent["intent_id"])
    if receipt is None:
        (t.root / "STOP").write_text("Launch outcome unknown and unreconciled; investigate before any further action.\n")
        t.add("launch_receipt", "launch/receipt.json", {"protocol": "fly-choice-v1", "run_id": t.run_id, "intent_sha256": intent_sha, "status": "UNRESOLVED", "submission": result.to_dict(), "receipt": None})
        raise LaunchHalted("Launch outcome unresolved; STOP file written")
    if receipt.intent_sha256 != intent_sha or receipt.mint != unsigned.expected_mint:
        raise LaunchHalted("Reconciled receipt does not match the persisted intent")
    if receipt.metadata["name"] != intent["name"] or receipt.metadata["symbol"] != intent["ticker"]:
        raise LaunchHalted("On-venue metadata does not match the fly-selected identity")
    artifact = {
        "protocol": "fly-choice-v1",
        "run_id": t.run_id,
        "intent_sha256": intent_sha,
        "status": "CONFIRMED" if result.status == "CONFIRMED" else "RECONCILED",
        "submission": result.to_dict(),
        "receipt": receipt.to_dict(),
    }
    sha = t.add("launch_receipt", "launch/receipt.json", artifact)
    t.committer.commit("launch_receipt", sha, receipt.mint)
    log(f"launch receipt {sha[:16]}: mint {receipt.mint} on {receipt.network} ({'simulated' if receipt.simulated else 'live'})")
    return artifact, sha
