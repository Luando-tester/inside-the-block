"""Solana keypair handling.

A Solana keypair file is a JSON array of 64 bytes: 32-byte seed || 32-byte
public key. This project keeps ONE project keypair file (gitignored, chmod 600)
holding a dict:

    {
      "main":    [...64 ints...],          # funder + path-control sender
      "senders": [[...64 ints...], ...],   # 7 sender keypairs S1..S7
    }

All 8 accounts are project-owned and funded to the rent-exempt minimum, so every
probe transfer moves a few lamports between two existing, funded accounts and every
lamport is recoverable by the end-of-campaign sweep. No external wallet is ever
loaded by this tool; the file path arrives via the PROBE_KEYPAIR_FILE
environment variable in live mode.
"""

import json
import os

from . import ed25519
from .base58 import b58encode


class Keypair:
    def __init__(self, seed: bytes):
        if len(seed) != 32:
            raise ValueError("seed must be 32 bytes")
        self.seed = seed
        self.public_key = ed25519.public_key_from_seed(seed)

    @property
    def pubkey(self) -> str:
        return b58encode(self.public_key)

    def sign(self, message: bytes) -> bytes:
        return ed25519.sign(self.seed, message)

    def to_json_bytes(self):
        return list(self.seed + self.public_key)

    @classmethod
    def from_json_bytes(cls, arr):
        if len(arr) != 64:
            raise ValueError("keypair array must have 64 entries")
        seed = bytes(arr[:32])
        kp = cls(seed)
        if kp.public_key != bytes(arr[32:]):
            raise ValueError("keypair public key does not match seed")
        return kp

    @classmethod
    def generate(cls) -> "Keypair":
        return cls(os.urandom(32))


class KeypairSet:
    """main + senders, in deterministic roles (see plan.py for assignments)."""

    def __init__(self, main: Keypair, senders):
        self.main = main
        self.senders = list(senders)

    def all_accounts(self):
        """All project accounts as Keypairs: [main, S1, ..., S7]."""
        return [self.main] + self.senders

    def by_pubkey(self):
        return {kp.pubkey: kp for kp in self.all_accounts()}

    def to_dict(self):
        return {
            "main": self.main.to_json_bytes(),
            "senders": [kp.to_json_bytes() for kp in self.senders],
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            Keypair.from_json_bytes(d["main"]),
            [Keypair.from_json_bytes(a) for a in d["senders"]],
        )

    @classmethod
    def generate(cls, n_senders: int = 7) -> "KeypairSet":
        return cls(Keypair.generate(), [Keypair.generate() for _ in range(n_senders)])

    def save(self, path: str):
        with open(path, "w") as fh:
            json.dump(self.to_dict(), fh)
        os.chmod(path, 0o600)

    @classmethod
    def load(cls, path: str) -> "KeypairSet":
        with open(path) as fh:
            return cls.from_dict(json.load(fh))
