import json

import pytest

from flybrain.cli import main
from flybrain.launch import pons
from flybrain.launch.base import build_intent
from flybrain.launch.evm import encode, encode_call, keccak256, selector, to_checksum
from flybrain.risk.policy import LaunchGuard, LaunchSettings, Veto
from flybrain.run import run
from tests.conftest import small_manifest, write_fixture_checkpoint, write_manifest


def test_keccak_known_answers():
    assert keccak256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
    assert keccak256(b"abc").hex() == "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45"
    assert keccak256(b"a" * 200).hex() == keccak256(b"a" * 200).hex() and len(keccak256(b"x" * 1000)) == 32
    assert selector("transfer(address,uint256)").hex() == "a9059cbb"
    assert to_checksum("0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed") == "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed"


def test_abi_encoding_known_layout():
    enc = encode(("uint256", "string"), (1, "hi"))
    assert enc.hex() == (
        "0000000000000000000000000000000000000000000000000000000000000001"
        "0000000000000000000000000000000000000000000000000000000000000040"
        "0000000000000000000000000000000000000000000000000000000000000002"
        "6869000000000000000000000000000000000000000000000000000000000000"
    )
    # dynamic tuple inside a call: head offset, then the tuple body with its own offsets
    data = encode_call("f", (("string", "bool"), "uint8"), (("ab", True), 7))
    assert data[:4] == selector("f((string,bool),uint8)")
    body = data[4:]
    assert int.from_bytes(body[0:32], "big") == 64 and int.from_bytes(body[32:64], "big") == 7
    tup = body[64:]
    assert int.from_bytes(tup[0:32], "big") == 64 and int.from_bytes(tup[32:64], "big") == 1 and tup[64:96] == (2).to_bytes(32, "big") and tup[96:98] == b"ab"
    with pytest.raises(ValueError):
        encode(("uint16",), (70000,))
    with pytest.raises(ValueError):
        encode(("address",), ("0x123",))


def test_launch_selector_matches_docs_signature():
    assert pons.LAUNCH_SIG == "launchToken((string,string,string,string,(string,string,string,string,string),address,uint16,bool,bytes32,bytes32),uint256,address)"
    assert len(pons.LAUNCH_SELECTOR) == 4 and pons.V2["factory"] == to_checksum(pons.V2["factory"])
    for addr in pons.V2.values():
        assert addr == to_checksum(addr), f"{addr} is not EIP-55 checksummed as published"


@pytest.fixture
def launched(tmp_path):
    cp = write_fixture_checkpoint(tmp_path)
    mpath = write_manifest(tmp_path, small_manifest(cp))
    s = run(mpath, cp, tmp_path / "run", run_id="pons-test", log=lambda *_: None)
    if s["outcome"] != "LAUNCH":
        pytest.skip("fixture did not launch")
    from flybrain.commitments.canonical import load_canonical

    final, fsha = load_canonical(tmp_path / "run" / "final" / "decision.json")
    manifest, _ = load_canonical(tmp_path / "run" / "manifest.json")
    final = {**final, "launch_venue": "pons"}
    settings = LaunchSettings(network=pons.NETWORK, allowed_networks=())
    intent = build_intent(final, fsha, manifest, "pons-test", settings, "0" * 64)
    return tmp_path, intent, final, fsha


def test_pons_offline_build_inspect_and_refuse_submit(launched):
    tmp_path, intent, final, fsha = launched
    a = pons.PonsAdapter(tmp_path / "ledger", creator_fee_recipient="0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed")
    pre = a.preflight(intent)
    assert not pre.ok  # offline: fee and economics pin not read; audit/testnet gates fail by design
    failed = {c["check"] for c in pre.checks if not c["ok"]}
    assert {"launch_fee_read", "economics_pinned", "audit", "testnet"} <= failed
    u = a.build_unsigned(intent)
    assert u.payload[:4] == pons.LAUNCH_SELECTOR and u.program_ids == [pons.V2["factory"]]
    d = u.instructions[0]["data"]
    assert d["name"] == intent["name"] and d["symbol"] == intent["ticker"] and d["creatorTaxBps"] == 0 and d["buybackEnabled"] is False
    assert d["salt"] == "0x" + pons.decision_salt(fsha).hex()
    problems = pons.PonsAdapter.inspect(u, intent, None)
    assert any("launchFee" in p for p in problems) and any("expectedEconomics" in p for p in problems)
    # With fee and pin supplied (as a live preflight would), inspection is clean.
    b = pons.PonsAdapter(tmp_path / "ledger2", creator_fee_recipient="0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed", launch_fee_wei=500000000000000, expected_economics=b"\x11" * 32)
    u2 = b.build_unsigned(intent)
    assert pons.PonsAdapter.inspect(u2, intent, 500000000000000) == []
    assert pons.PonsAdapter.inspect(u2, intent, 1) == ["value must equal launchFee() read immediately before launch"]
    assert "token params differ" in pons.PonsAdapter.inspect(u2, {**intent, "ticker": "OTHER"}, 500000000000000)[0]
    r = b.submit(b"anything")
    assert r.status == "REJECTED" and "disabled" in r.detail and b.reconcile(intent["intent_id"]) is None
    with pytest.raises(ValueError):
        b.call("eth_sendRawTransaction", ["0x"])


def test_guard_treats_robinhood_chain_as_mainnet():
    with pytest.raises(Veto, match="Mainnet"):
        LaunchGuard(LaunchSettings(network="robinhood-chain")).check_settings()


def test_pons_preview_cli_exports_without_submitting(launched, capsys):
    tmp_path, intent, final, fsha = launched
    from flybrain.commitments.canonical import write_canonical

    # Rewrite the recorded final decision's venue to pons for the preview
    # (the chain is not re-linked; the preview reads the file, it does not verify).
    write_canonical(tmp_path / "run" / "final" / "decision.json", final)
    code = main(["pons-preview", "--run", str(tmp_path / "run"), "--creator-fee-recipient", "0x5aaeb6053f3e94c9b9a09f33669435e7ef1beaed"])
    out = json.loads(capsys.readouterr().out)
    assert code == 1 and out["preflight_ok"] is False
    export = json.loads((tmp_path / "run" / "launch" / "pons-preview.json").read_text())
    assert export["chain_id"] == 4663 and export["unsigned"]["instructions"][0]["data"]["tx"]["to"] == pons.V2["factory"]
    assert "disabled" in export["submission"]
    assert not list((tmp_path / "run" / "launch" / "pons-ledger").glob("*")), "preview must not record any submission"
