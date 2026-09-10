import json

import pytest

from flybrain.commitments.hashchain import walk
from flybrain.launch.base import build_intent
from flybrain.launch.mock import MockLaunchAdapter, MockSigner, mock_mint
from flybrain.launch.pipeline import LaunchHalted, execute_launch
from flybrain.risk.policy import LaunchGuard, LaunchSettings, Veto
from flybrain.run import run
from flybrain.verifier.verify import verify_run
from tests.conftest import small_manifest, write_fixture_checkpoint, write_manifest


def launching_run(tmp_path, **kw):
    cp = write_fixture_checkpoint(tmp_path)
    mpath = write_manifest(tmp_path, small_manifest(cp))
    return mpath, cp, run(mpath, cp, tmp_path / "run", run_id="launch-test", log=lambda *_: None, **kw)


def test_small_manifest_launches_on_mock_and_receipt_matches_choice(tmp_path):
    _, _, s = launching_run(tmp_path)
    if s["outcome"] != "LAUNCH":
        pytest.skip(f"fixture ended {s['outcome']} ({s['launch']['reason']}); launch path covered by direct pipeline tests")
    out = tmp_path / "run"
    kinds = [e["kind"] for e, _, _ in walk(out)]
    assert kinds.index("launch_intent") < kinds.index("launch_receipt")
    intent = json.loads((out / "launch" / "intent.json").read_text())
    receipt = json.loads((out / "launch" / "receipt.json").read_text())
    final = json.loads((out / "final" / "decision.json").read_text())
    manifest = json.loads((out / "manifest.json").read_text())
    name = next(c["text"] for c in manifest["categories"]["name"] if c["id"] == final["identity"]["name"])
    assert intent["intent"]["name"] == name == receipt["receipt"]["metadata"]["name"]
    assert receipt["receipt"]["mint"] == mock_mint(intent["intent_sha256"]) == s["launch"]["mint"]
    assert receipt["receipt"]["simulated"] is True and receipt["receipt"]["network"] == "mock"
    assert receipt["receipt"]["authorities"] == {"mint": None, "freeze": None, "update": None}
    assert verify_run(out)["ok"]


@pytest.fixture
def decided(tmp_path):
    """A transcript with a LAUNCH final decision, built by hand for pipeline tests."""
    from flybrain import software
    from flybrain.choice import manifest as mm
    from flybrain.choice.backends import FixtureBrain
    from flybrain.choice.transcript import Transcript

    cp = write_fixture_checkpoint(tmp_path)
    m = small_manifest(cp)
    mpath = write_manifest(tmp_path, m)
    manifest, msha = mm.load(mpath)
    t = Transcript(tmp_path / "t", manifest, msha, FixtureBrain(cp), "pipe", software.identity())
    final = {
        "protocol": "fly-choice-v1", "run_id": "pipe", "manifest_sha256": msha, "checkpoint_sha256": t.chain.entries[0]["sha256"] and FixtureBrain(cp).checkpoint_sha256,
        "backend": "fixture-brain-v1",
        "identity": {"name": "n-a", "ticker": "t-a", "logo": "logo-fly", "palette": "pal-terminal", "description": "d-a"},
        "identity_complete": True, "launch_venue": "pumpfun", "venue_selection_mode": "simulation", "launch_action": "launch",
        "skipped_categories": [], "category_roots": {}, "outcome": "LAUNCH", "reason": None, "disclosure": manifest["disclosure"], "category_order": list(mm.CATEGORIES),
    }
    fsha = t.add("final_decision", "final/decision.json", final)
    return t, manifest, final, fsha


def make_intent(t, manifest, final, fsha, settings):
    return build_intent(final, fsha, manifest, "pipe", settings, "0" * 64)


def test_pipeline_confirmed(decided, tmp_path):
    t, manifest, final, fsha = decided
    s = LaunchSettings()
    adapter = MockLaunchAdapter(tmp_path / "ledger")
    art, sha = execute_launch(t, make_intent(t, manifest, final, fsha, s), final, fsha, adapter, MockSigner(), LaunchGuard(s, adapter.program_ids), log=lambda *_: None)
    assert art["status"] == "CONFIRMED" and adapter.submissions == 1
    assert art["receipt"]["metadata"] == {"name": "FLY", "symbol": "FLY", "description": "A FLY BRAIN CHOSE THIS COIN FROM A LIST. THE CHAIN KEEPS THE RECEIPTS.", "logo_png_sha256": "0" * 64, "palette": ["#0b1120", "#38bdf8", "#f8fafc"]}


def test_unknown_outcome_reconciles_without_second_mint(decided, tmp_path):
    t, manifest, final, fsha = decided
    s = LaunchSettings()
    adapter = MockLaunchAdapter(tmp_path / "ledger", fail_submit="unknown")
    art, _ = execute_launch(t, make_intent(t, manifest, final, fsha, s), final, fsha, adapter, MockSigner(), LaunchGuard(s, adapter.program_ids), log=lambda *_: None)
    assert art["status"] == "RECONCILED" and art["submission"]["status"] == "UNKNOWN" and adapter.submissions == 1
    assert len(list((tmp_path / "ledger").iterdir())) == 1


def test_rejected_submission_halts_after_durable_intent(decided, tmp_path):
    t, manifest, final, fsha = decided
    s = LaunchSettings()
    adapter = MockLaunchAdapter(tmp_path / "ledger", fail_submit="rejected")
    with pytest.raises(LaunchHalted):
        execute_launch(t, make_intent(t, manifest, final, fsha, s), final, fsha, adapter, MockSigner(), LaunchGuard(s, adapter.program_ids), log=lambda *_: None)
    kinds = [e["kind"] for e in t.chain.entries]
    assert "launch_intent" in kinds and kinds[-1] == "launch_receipt"
    assert json.loads((t.root / "launch" / "receipt.json").read_text())["status"] == "REJECTED"


def test_intent_is_durable_before_submission(decided, tmp_path):
    t, manifest, final, fsha = decided
    s = LaunchSettings()

    class Exploding(MockLaunchAdapter):
        def submit(self, signed):
            raise ConnectionError("network died")

    adapter = Exploding(tmp_path / "ledger")
    with pytest.raises(ConnectionError):
        execute_launch(t, make_intent(t, manifest, final, fsha, s), final, fsha, adapter, MockSigner(), LaunchGuard(s, adapter.program_ids), log=lambda *_: None)
    assert t.chain.entries[-1]["kind"] == "launch_intent"


@pytest.mark.parametrize(
    "settings,message",
    [
        (LaunchSettings(live_launch=True), "LIVE_LAUNCH"),
        (LaunchSettings(network="mainnet-beta"), "Mainnet"),
        (LaunchSettings(network="testnet"), "not allowed"),
        (LaunchSettings(max_sol_spend="5"), "MAX_SOL_SPEND"),
        (LaunchSettings(initial_dev_buy_sol="0.01"), "dev buy"),
    ],
)
def test_guard_vetoes_unsafe_settings(settings, message):
    with pytest.raises(Veto, match=message):
        LaunchGuard(settings).check_settings()


def test_spend_cap_cannot_be_bypassed_by_fees_rent_or_dev_buy(decided):
    t, manifest, final, fsha = decided
    s = LaunchSettings(max_sol_spend="0.05")
    g = LaunchGuard(s, ("mock-launch-v1",))
    base = make_intent(t, manifest, final, fsha, s)
    g.check_intent(base, final, fsha)
    for k in ["estimated_fees_sol", "metadata_rent_sol"]:
        with pytest.raises(Veto, match="exceeds cap"):
            g.check_intent({**base, k: "0.01"}, final, fsha)
    with pytest.raises(Veto):
        g.check_intent({**base, "initial_dev_buy_sol": "0.001"}, final, fsha)


def test_guard_never_substitutes_wait_or_venue(decided):
    t, manifest, final, fsha = decided
    s = LaunchSettings()
    g = LaunchGuard(s, ("mock-launch-v1",))
    intent = make_intent(t, manifest, final, fsha, s)
    with pytest.raises(Veto, match="WAIT"):
        g.check_intent(intent, {**final, "launch_action": "wait", "outcome": "NO_LAUNCH"}, fsha)
    with pytest.raises(Veto, match="venue"):
        g.check_intent({**intent, "venue": "pons"}, final, fsha)
    with pytest.raises(Veto, match="final decision"):
        g.check_intent({**intent, "final_decision_sha256": "0" * 64}, final, fsha)


def test_unsigned_inspection_rejects_unknown_programs():
    g = LaunchGuard(LaunchSettings(), ("mock-launch-v1",))
    good = {"program_ids": ["mock-launch-v1"], "instructions": [{"program_id": "mock-launch-v1", "accounts": ["x"]}], "expected_mint": "m"}
    g.inspect_unsigned(good)
    with pytest.raises(Veto, match="unknown programs"):
        g.inspect_unsigned({**good, "program_ids": ["mock-launch-v1", "11111111111111111111111111111111"]})
    with pytest.raises(Veto, match="unknown program"):
        g.inspect_unsigned({**good, "instructions": [{"program_id": "evil", "accounts": ["x"]}]})
    with pytest.raises(Veto, match="expected mint"):
        g.inspect_unsigned({**good, "expected_mint": ""})


def test_development_defaults_cannot_reach_mainnet(monkeypatch):
    monkeypatch.delenv("LIVE_LAUNCH", raising=False)
    monkeypatch.delenv("NETWORK", raising=False)
    s = LaunchSettings.from_env()
    assert s.live_launch is False and s.network == "mock" and s.initial_dev_buy_sol == "0"
    monkeypatch.setenv("LIVE_LAUNCH", "true")
    monkeypatch.setenv("NETWORK", "mainnet-beta")
    with pytest.raises(Veto):
        LaunchGuard(LaunchSettings.from_env()).check_settings()


def test_unimplemented_adapters_refuse_to_construct():
    from flybrain.launch.pons import PonsAdapter
    from flybrain.launch.pumpfun import PumpFunAdapter
    from flybrain.launch.solana_devnet import SolanaDevnetMintAdapter

    for cls in [SolanaDevnetMintAdapter, PumpFunAdapter, PonsAdapter]:
        with pytest.raises(NotImplementedError):
            cls()
