"""Legacy Solana transaction construction (System transfer + Compute Budget).

A probe transaction is deliberately minimal:
  1. ComputeBudget::SetComputeUnitLimit(cu_limit)
  2. ComputeBudget::SetComputeUnitPrice(price_micro_lamports_per_cu)
  3. SystemProgram::Transfer(dust amount) from the payer to a project account

The priority fee charged is price * cu_limit micro-lamports regardless of the
tiny real compute used; the base fee is 5,000 lamports for the single signature.
"""

import base64
import struct

from .base58 import b58decode, b58encode

SYSTEM_PROGRAM = "11111111111111111111111111111111"
COMPUTE_BUDGET_PROGRAM = "ComputeBudget111111111111111111111111111111"
BASE_FEE_PER_SIGNATURE_LAMPORTS = 5000


def _shortvec(n: int) -> bytes:
    out = bytearray()
    while True:
        byte = n & 0x7F
        n >>= 7
        if n:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def priority_fee_lamports(price_micro_lamports_per_cu: int, cu_limit: int) -> int:
    return (price_micro_lamports_per_cu * cu_limit) // 1_000_000


def total_fee_lamports(price_micro_lamports_per_cu: int, cu_limit: int) -> int:
    return BASE_FEE_PER_SIGNATURE_LAMPORTS + priority_fee_lamports(
        price_micro_lamports_per_cu, cu_limit
    )


class _Instruction:
    def __init__(self, program: str, accounts, data: bytes):
        # accounts: list of (pubkey_b58, is_signer, is_writable)
        self.program = program
        self.accounts = list(accounts)
        self.data = data


def _compile_message(payer_pubkey: str, instructions, blockhash_b58: str) -> bytes:
    metas = {}  # pubkey -> [is_signer, is_writable]

    def add(pubkey, is_signer, is_writable):
        if pubkey in metas:
            metas[pubkey][0] = metas[pubkey][0] or is_signer
            metas[pubkey][1] = metas[pubkey][1] or is_writable
        else:
            metas[pubkey] = [is_signer, is_writable]

    add(payer_pubkey, True, True)
    for ix in instructions:
        for pubkey, is_signer, is_writable in ix.accounts:
            add(pubkey, is_signer, is_writable)
        add(ix.program, False, False)

    def sort_key(item):
        pubkey, (is_signer, is_writable) = item
        if pubkey == payer_pubkey:
            return (0, pubkey)
        if is_signer and is_writable:
            return (1, pubkey)
        if is_signer:
            return (2, pubkey)
        if is_writable:
            return (3, pubkey)
        return (4, pubkey)

    ordered = sorted(metas.items(), key=sort_key)
    keys = [pubkey for pubkey, _ in ordered]
    index = {pubkey: i for i, pubkey in enumerate(keys)}
    num_signers = sum(1 for _, (s, _w) in ordered if s)
    num_ro_signed = sum(1 for _, (s, w) in ordered if s and not w)
    num_ro_unsigned = sum(1 for _, (s, w) in ordered if not s and not w)

    msg = bytearray()
    msg += bytes([num_signers, num_ro_signed, num_ro_unsigned])
    msg += _shortvec(len(keys))
    for pubkey in keys:
        msg += b58decode(pubkey)
    msg += b58decode(blockhash_b58)
    msg += _shortvec(len(instructions))
    for ix in instructions:
        msg.append(index[ix.program])
        acct_idx = [index[pk] for pk, _s, _w in ix.accounts]
        msg += _shortvec(len(acct_idx))
        msg += bytes(acct_idx)
        msg += _shortvec(len(ix.data))
        msg += ix.data
    return bytes(msg)


def build_probe_transaction(payer, recipient_pubkey: str, price_micro_lamports_per_cu: int,
                            cu_limit: int, transfer_lamports: int, blockhash_b58: str):
    """Build + sign a probe transaction.

    `payer` is a probe.keypair.Keypair. Returns (base64_tx, signature_b58).
    """
    payer_pubkey = payer.pubkey
    instructions = [
        _Instruction(
            COMPUTE_BUDGET_PROGRAM, [], bytes([2]) + struct.pack("<I", cu_limit)
        ),
        _Instruction(
            COMPUTE_BUDGET_PROGRAM,
            [],
            bytes([3]) + struct.pack("<Q", price_micro_lamports_per_cu),
        ),
        _Instruction(
            SYSTEM_PROGRAM,
            [(payer_pubkey, True, True), (recipient_pubkey, False, True)],
            struct.pack("<I", 2) + struct.pack("<Q", transfer_lamports),
        ),
    ]
    message = _compile_message(payer_pubkey, instructions, blockhash_b58)
    signature = payer.sign(message)
    tx = _shortvec(1) + signature + message
    return base64.b64encode(tx).decode(), b58encode(signature)
