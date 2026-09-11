"""pons v2 launch adapter (Robinhood Chain, chain id 4663). Gate C: build and
inspect only. Submission is disabled in this build.

Source of truth: https://docs.ponsfamily.com/docs/v2 (read 2026-09-11).
Findings that shape this adapter (see docs/pons.md):
- pons is an EVM launch protocol on Robinhood Chain, not Solana. Choosing
  pons over Pump.fun is therefore also a chain choice.
- Launching is one payable call: ``launchToken(TokenParams, launchConfigId,
  pairToken)`` on the v2 factory; the launch fee is ``msg.value`` and must be
  read from ``launchFee()``; ``expectedEconomics`` must be pinned from
  ``previewLaunchEconomics`` right before launch or the call reverts.
- No HTTP API is in the trust path; no testnet deployment exists; v2 is
  unaudited until reports are published. So there is nowhere safe to submit
  from a development build: this adapter never signs and never sends.
- The 32-byte CREATE2 ``salt`` is derived from the final-decision hash, which
  binds the eventual token address to the fly's recorded choice.
"""

import json
import urllib.request
from pathlib import Path

from ..commitments.canonical import canonical_bytes, sha256_hex
from .base import FinalLaunchReceipt, PreflightResult, SubmissionResult, UnsignedTransaction
from .evm import encode, encode_call, keccak256, selector, to_checksum

DOCS = "https://docs.ponsfamily.com/docs/v2"
DOCS_CHECKED = "2026-09-11"
NETWORK = "robinhood-chain"
CHAIN_ID = 4663
PUBLIC_RPC = "https://rpc.mainnet.chain.robinhood.com"
EXPLORER = "https://robinhoodchain.blockscout.com"
ZERO = "0x0000000000000000000000000000000000000000"
V2 = {
    "factory": "0x7eD598BcEf8bd9Edd8C97A195C6d13f40801EC7e",
    "meme_hook": "0xE5e702641Ea86F4ae6cC3cDaeD2B886f976Be044",
    "fee_escrow": "0xd3AFEB2a57f70eF218Aa82451c51B2fb0416Ac9e",
    "buyback_vault": "0x42df2a798f82289E177311362e8f5ccC45c1219c",
    "launch_locker": "0x267444D099b10fB5Ed7c3Cc7B7c767AdcA574952",
    "launch_and_buy": "0xe33E9E479dF8802cb0866d5d05258bEc4cF62948",
    "launch_deployer": "0x3711ceA4feaDE896C913C68F01Eda97Cb06D1A42",
    "graduation_executor": "0xC7819B64A1dAECD7eC19856d026cb14EfBd89046",
    "graduation_guard": "0xf5695117b99B6f6401e67d4195BD653628176C6C",
}
V1 = {
    "factory": "0xA5aAb3F0c6EeadF30Ef1D3Eb997108E976351feB",
    "locker": "0x736D76699C26D0d966744cAe304C000d471f7F35",
    "weth": "0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73",
    "token_launched_topic0": "0xdb51ea9ad51ab453a65a4cb7e60c3cb378c9501bb002609f8f97778fb6c4235a",
}
SOCIALS_T = ("string", "string", "string", "string", "string")
TOKEN_PARAMS_T = ("string", "string", "string", "string", SOCIALS_T, "address", "uint16", "bool", "bytes32", "bytes32")
LAUNCH_T = (TOKEN_PARAMS_T, "uint256", "address")
LAUNCH_SIG = "launchToken((string,string,string,string,(string,string,string,string,string),address,uint16,bool,bytes32,bytes32),uint256,address)"
LAUNCH_SELECTOR = selector(LAUNCH_SIG)
READ_ONLY_METHODS = ("eth_chainId", "eth_getCode", "eth_call", "eth_blockNumber", "eth_getLogs")
FN_LAUNCH_FEE = selector("launchFee()")
FN_PREVIEW = selector("previewLaunchEconomics(uint256,address)")
FN_CONFIG_COUNT = selector("launchConfigCount()")


def decision_salt(final_decision_sha256: str) -> bytes:
    return keccak256(b"flybrain:pons:salt:" + final_decision_sha256.encode())


class PonsAdapter:
    name = "pons"
    network = NETWORK
    program_ids = (V2["factory"],)
    simulation = True

    def __init__(self, ledger_dir, rpc: str | None = None, creator_fee_recipient: str | None = None, launch_config_id: int = 0, pair_token: str = ZERO, launch_fee_wei: int | None = None, expected_economics: bytes | None = None, logo_uri: str | None = None):
        self.ledger = Path(ledger_dir)
        self.ledger.mkdir(parents=True, exist_ok=True)
        self.rpc = rpc
        self.creator_fee_recipient = to_checksum(creator_fee_recipient) if creator_fee_recipient else None
        self.launch_config_id = int(launch_config_id)
        self.pair_token = to_checksum(pair_token)
        self.launch_fee_wei = launch_fee_wei
        self.expected_economics = expected_economics
        self.logo_uri = logo_uri
        self.submissions = 0

    # ---------------------------------------------------------------- rpc
    def call(self, method: str, params: list):
        if method not in READ_ONLY_METHODS:
            raise ValueError(f"{method} is not a read-only method; this adapter never sends transactions")
        if not self.rpc:
            raise RuntimeError("offline: no RPC configured")
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        req = urllib.request.Request(self.rpc, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            out = json.loads(r.read().decode())
        if "error" in out:
            raise RuntimeError(f"rpc {method}: {out['error']}")
        return out["result"]

    def read_factory(self, data: bytes) -> bytes:
        res = self.call("eth_call", [{"to": V2["factory"], "data": "0x" + data.hex()}, "latest"])
        return bytes.fromhex(res[2:])

    # ---------------------------------------------------------- interface
    def preflight(self, intent: dict) -> PreflightResult:
        checks = [
            {"check": "network", "ok": intent["network"] == NETWORK, "detail": f"{intent['network']} (chain id {CHAIN_ID})"},
            {"check": "venue", "ok": intent["venue"] == "pons", "detail": intent["venue"]},
            {"check": "creator_fee_recipient", "ok": bool(self.creator_fee_recipient), "detail": self.creator_fee_recipient or "unset: pons pays creator fees to this address; it must be a disclosed treasury"},
            {"check": "no_dev_buy", "ok": str(intent.get("initial_dev_buy_sol", "0")) == "0", "detail": "launchToken only; LaunchAndBuy contract is not used"},
            {"check": "no_prior_intent", "ok": not (self.ledger / f"{intent['intent_id']}.json").exists(), "detail": intent["intent_id"]},
            {"check": "audit", "ok": False, "detail": "pons v2 is unaudited per its docs; do not launch until audit reports are published and reviewed"},
            {"check": "testnet", "ok": False, "detail": "no pons testnet exists; the only deployment is a live chain"},
        ]
        if self.rpc:
            try:
                chain = int(self.call("eth_chainId", []), 16)
                checks.append({"check": "rpc_chain_id", "ok": chain == CHAIN_ID, "detail": str(chain)})
                code = self.call("eth_getCode", [V2["factory"], "latest"])
                checks.append({"check": "factory_code_present", "ok": len(code) > 4, "detail": f"{len(code) // 2 - 1} bytes"})
                fee = int.from_bytes(self.read_factory(FN_LAUNCH_FEE), "big")
                self.launch_fee_wei = fee
                checks.append({"check": "launch_fee_read", "ok": True, "detail": f"{fee} wei"})
                pin = self.read_factory(FN_PREVIEW + encode(("uint256", "address"), (self.launch_config_id, self.pair_token)))
                self.expected_economics = pin[:32]
                checks.append({"check": "economics_pinned", "ok": len(pin) >= 32, "detail": "0x" + pin[:32].hex()})
                count = int.from_bytes(self.read_factory(FN_CONFIG_COUNT), "big")
                checks.append({"check": "launch_config_exists", "ok": self.launch_config_id < count, "detail": f"id {self.launch_config_id} of {count}"})
            except Exception as e:  # network failures are preflight failures, never retries into a send
                checks.append({"check": "rpc", "ok": False, "detail": f"{type(e).__name__}: {e}"})
        else:
            checks.append({"check": "launch_fee_read", "ok": self.launch_fee_wei is not None, "detail": "offline: launchFee() not read" if self.launch_fee_wei is None else f"{self.launch_fee_wei} wei (supplied)"})
            checks.append({"check": "economics_pinned", "ok": self.expected_economics is not None, "detail": "offline: previewLaunchEconomics() not read" if self.expected_economics is None else "supplied"})
        return PreflightResult(all(c["ok"] for c in checks), NETWORK, checks)

    def token_params(self, intent: dict) -> tuple:
        salt = decision_salt(intent["final_decision_sha256"])
        pin = self.expected_economics or b"\0" * 32
        return (
            intent["name"],
            intent["ticker"],
            self.logo_uri or f"sha256:{intent['logo_png_sha256']}",
            intent["description"],
            ("", "", "", "", ""),
            self.creator_fee_recipient or ZERO,
            0,  # creatorTaxBps: no creator tax
            False,  # buybackEnabled: the project must not buy its own token
            pin,
            salt,
        )

    def build_unsigned(self, intent: dict) -> UnsignedTransaction:
        params = self.token_params(intent)
        calldata = encode_call("launchToken", LAUNCH_T, (params, self.launch_config_id, self.pair_token))
        salt_hex = "0x" + params[9].hex()
        decoded = {
            "name": params[0], "symbol": params[1], "logo": params[2], "description": params[3],
            "socials": {"twitter": "", "telegram": "", "discord": "", "website": "", "farcaster": ""},
            "creatorFeeRecipient": params[5], "creatorTaxBps": 0, "buybackEnabled": False,
            "expectedEconomics": "0x" + params[8].hex(), "expectedEconomicsPinned": self.expected_economics is not None,
            "salt": salt_hex, "launchConfigId": self.launch_config_id, "pairToken": self.pair_token,
        }
        tx = {
            "chainId": CHAIN_ID,
            "to": V2["factory"],
            "value_wei": self.launch_fee_wei,
            "data": "0x" + calldata.hex(),
            "selector": "0x" + LAUNCH_SELECTOR.hex(),
            "function": LAUNCH_SIG,
        }
        instructions = [{"program_id": V2["factory"], "name": "launchToken", "accounts": [V2["factory"], self.pair_token, params[5]], "data": {**decoded, "tx": tx}}]
        expected = f"create2-pending:{salt_hex}"  # predictLaunchAddresses signature not published; resolved at reconcile
        return UnsignedTransaction([V2["factory"]], instructions, expected, calldata, sha256_hex(calldata))

    @staticmethod
    def inspect(unsigned: UnsignedTransaction, intent: dict, launch_fee_wei: int | None) -> list:
        """Independent re-derivation of every byte before anyone could sign."""
        problems = []
        if list(unsigned.program_ids) != [V2["factory"]]:
            problems.append("program_ids must be exactly the pinned v2 factory")
        if len(unsigned.instructions) != 1:
            problems.append("exactly one instruction expected")
            return problems
        ix = unsigned.instructions[0]
        d = ix["data"]
        tx = d["tx"]
        if ix["program_id"] != V2["factory"] or tx["to"] != V2["factory"]:
            problems.append("call target is not the pinned factory")
        if tx["chainId"] != CHAIN_ID:
            problems.append(f"chainId {tx['chainId']} != {CHAIN_ID}")
        if launch_fee_wei is None or tx["value_wei"] != launch_fee_wei:
            problems.append("value must equal launchFee() read immediately before launch")
        if not d["expectedEconomicsPinned"]:
            problems.append("expectedEconomics not pinned from previewLaunchEconomics()")
        if d["name"] != intent["name"] or d["symbol"] != intent["ticker"] or d["description"] != intent["description"]:
            problems.append("token params differ from the fly-selected identity")
        if d["creatorTaxBps"] != 0 or d["buybackEnabled"]:
            problems.append("creator tax must be 0 and buybacks disabled")
        if d["salt"] != "0x" + decision_salt(intent["final_decision_sha256"]).hex():
            problems.append("salt does not derive from the final decision hash")
        params = (d["name"], d["symbol"], d["logo"], d["description"], tuple(d["socials"][k] for k in ["twitter", "telegram", "discord", "website", "farcaster"]), d["creatorFeeRecipient"], d["creatorTaxBps"], d["buybackEnabled"], bytes.fromhex(d["expectedEconomics"][2:]), bytes.fromhex(d["salt"][2:]))
        expected = encode_call("launchToken", LAUNCH_T, (params, d["launchConfigId"], d["pairToken"]))
        if "0x" + expected.hex() != tx["data"] or expected != unsigned.payload:
            problems.append("calldata does not re-encode from the decoded parameters")
        if unsigned.payload_sha256 != sha256_hex(unsigned.payload):
            problems.append("payload hash mismatch")
        return problems

    def submit(self, signed_transaction: bytes) -> SubmissionResult:
        self.submissions += 1
        return SubmissionResult("REJECTED", None, "Gate C: pons submission is disabled in this build (live chain, unaudited protocol, no testnet). Export with `flybrain pons-preview` for human review.")

    def reconcile(self, intent_id: str):
        # Without a published predictLaunchAddresses signature the token address
        # is learned from the TokenLaunched log of the submitted transaction.
        # No submission can happen from this build, so there is never a receipt.
        return None

    def export(self, intent: dict, unsigned: UnsignedTransaction, preflight: PreflightResult) -> dict:
        return {
            "adapter": "pons-v2",
            "docs": DOCS,
            "docs_checked": DOCS_CHECKED,
            "network": NETWORK,
            "chain_id": CHAIN_ID,
            "explorer": EXPLORER,
            "contracts": V2,
            "intent_sha256": sha256_hex(canonical_bytes(intent)),
            "preflight": preflight.to_dict(),
            "unsigned": unsigned.to_dict(),
            "inspection": self.inspect(unsigned, intent, self.launch_fee_wei),
            "submission": "disabled in this build; requires separate explicit human approval, audit review and a funded isolated signer",
        }


def __getattr__(name):  # keep the old placeholder name importable
    if name == "PonsPlaceholder":
        return PonsAdapter
    raise AttributeError(name)


__all__ = ["PonsAdapter", "V2", "V1", "CHAIN_ID", "NETWORK", "LAUNCH_SIG", "LAUNCH_SELECTOR", "decision_salt"]

FinalLaunchReceipt  # referenced for type completeness
