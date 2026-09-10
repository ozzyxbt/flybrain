"""Gate B: plain SPL token proof on Solana devnet. Not implemented in Gate A.

Implementation notes for the next gate (see docs/launch-safety.md):
- Build the mint + metadata transaction locally, pin program IDs
  (Token, Associated Token, Memo, the confirmed metadata program), simulate,
  inspect every instruction, then sign with an isolated low-balance signer.
- Revoke mint and freeze authority in the same transaction; verify on chain.
- Persist the intent before submission; reconcile by mint address on UNKNOWN.
"""


class SolanaDevnetMintAdapter:
    name = "solana-devnet"
    network = "devnet"
    program_ids = ()

    def __init__(self, *_, **__):
        raise NotImplementedError("SolanaDevnetMintAdapter is Gate B; this build launches on the mock adapter only")
