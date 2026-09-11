"""Launch policy guard: it may veto, it may never substitute.

Defaults are the development defaults from the build brief:
    LIVE_LAUNCH=false, NETWORK=devnet-or-mock, MAX_SOL_SPEND small,
    INITIAL_DEV_BUY=0 unless explicitly approved and disclosed.
"""

import os
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

# Any chain where real value moves. Robinhood Chain (pons) has no testnet, so
# the pons adapter is build/inspect only and never reaches this guard's send path.
MAINNET_NAMES = ("mainnet", "mainnet-beta", "robinhood-chain", "robinhood-mainnet", "chain-4663")


class Veto(Exception):
    pass


def _decimal(value, name):
    try:
        d = Decimal(str(value))
    except InvalidOperation as e:
        raise Veto(f"{name} is not a decimal") from e
    if not d.is_finite() or d < 0:
        raise Veto(f"{name} must be a finite nonnegative decimal")
    return d


@dataclass(frozen=True)
class LaunchSettings:
    live_launch: bool = False
    network: str = "mock"
    max_sol_spend: str = "0.05"
    initial_dev_buy_sol: str = "0"
    dev_buy_disclosed: bool = False
    allowed_networks: tuple = ("mock", "devnet")

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        return cls(
            live_launch=env.get("LIVE_LAUNCH", "false").lower() == "true",
            network=env.get("NETWORK", "mock"),
            max_sol_spend=env.get("MAX_SOL_SPEND", "0.05"),
            initial_dev_buy_sol=env.get("INITIAL_DEV_BUY", "0"),
            dev_buy_disclosed=env.get("DEV_BUY_DISCLOSED", "false").lower() == "true",
        )


@dataclass
class LaunchGuard:
    settings: LaunchSettings
    allowed_programs: tuple = field(default_factory=tuple)

    def check_settings(self):
        s = self.settings
        if s.live_launch:
            raise Veto("LIVE_LAUNCH=true is not supported by this build; mainnet activation is a separate reviewed gate")
        if s.network in MAINNET_NAMES:
            raise Veto("Mainnet is not an allowed network in this build")
        if s.network not in s.allowed_networks:
            raise Veto(f"Network {s.network!r} is not allowed; allowed: {s.allowed_networks}")
        cap = _decimal(s.max_sol_spend, "MAX_SOL_SPEND")
        if cap > Decimal("1"):
            raise Veto("MAX_SOL_SPEND above 1 SOL requires a reviewed configuration")
        buy = _decimal(s.initial_dev_buy_sol, "INITIAL_DEV_BUY")
        if buy > 0 and not s.dev_buy_disclosed:
            raise Veto("Initial dev buy must be zero unless explicitly approved and disclosed")
        return cap, buy

    def check_intent(self, intent: dict, final: dict, final_sha256: str):
        cap, buy = self.check_settings()
        if intent["final_decision_sha256"] != final_sha256:
            raise Veto("Intent does not reference the recorded final decision")
        if final["outcome"] != "LAUNCH" or final["launch_action"] != "launch":
            raise Veto("Final decision is not LAUNCH; the operator may not replace WAIT/NO_DECISION")
        if not final["identity_complete"]:
            raise Veto("Identity incomplete")
        if final["launch_venue"] is None or intent["venue"] != final["launch_venue"]:
            raise Veto("Intent venue differs from the fly-selected venue")
        if intent["network"] != self.settings.network:
            raise Veto("Intent network differs from configured network")
        total = _decimal(intent["max_sol_spend"], "intent.max_sol_spend") + _decimal(intent["initial_dev_buy_sol"], "intent.initial_dev_buy_sol") + _decimal(intent.get("estimated_fees_sol", "0"), "intent.estimated_fees_sol") + _decimal(intent.get("metadata_rent_sol", "0"), "intent.metadata_rent_sol")
        if total > cap:
            raise Veto(f"Total spend {total} SOL exceeds cap {cap} SOL (fees, rent and dev buy count)")
        if _decimal(intent["initial_dev_buy_sol"], "intent.initial_dev_buy_sol") != buy:
            raise Veto("Intent dev buy differs from configured, disclosed dev buy")
        for k in ["name", "ticker", "description", "logo_id", "palette_id"]:
            if k not in intent or not intent[k]:
                raise Veto(f"Intent missing {k}")

    def inspect_unsigned(self, unsigned: dict):
        programs = set(unsigned.get("program_ids", []))
        unknown = programs - set(self.allowed_programs)
        if unknown or not programs:
            raise Veto(f"Unsigned transaction touches unknown programs: {sorted(unknown) or 'none'}")
        for ix in unsigned.get("instructions", []):
            if ix.get("program_id") not in self.allowed_programs:
                raise Veto(f"Instruction for unknown program {ix.get('program_id')!r}")
            for acct in ix.get("accounts", []):
                if not isinstance(acct, str) or not acct:
                    raise Veto("Instruction references an invalid account")
        if not unsigned.get("expected_mint"):
            raise Veto("Unsigned transaction does not declare the expected mint")
