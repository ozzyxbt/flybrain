"""Placeholder: 'Pons' has no verified public URL, program ID or documentation.

Do not guess which product is intended. This stays unimplemented until the
owner supplies the exact official URL/account/documentation and it is
reviewed. Until then venue selection runs in simulation mode only.
"""


class PonsAdapter:
    name = "pons"
    network = "unknown"
    program_ids = ()

    def __init__(self, *_, **__):
        raise NotImplementedError("PonsAdapter: official identity/docs not supplied; unimplemented by design")
