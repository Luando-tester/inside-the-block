"""Append-only spend ledger + cumulative fee-cap enforcement.

Every live send is recorded BEFORE it is broadcast (status "attempted") and
updated after. Before any send, the executor asks the ledger whether the
send's fee still fits under the configured cumulative cap — counting every
previous attempt, including failed ones, because failed transactions on
Solana still pay their fee. If the cap would be exceeded, the send is
refused and the campaign stops. There is no override flag.
"""

import json
import os


class CapExceeded(Exception):
    pass


class SpendLedger:
    def __init__(self, data_dir: str, cap_lamports):
        self.path = os.path.join(data_dir, "spend_ledger.jsonl")
        self.cap_lamports = cap_lamports
        os.makedirs(data_dir, exist_ok=True)

    def entries(self):
        if not os.path.exists(self.path):
            return []
        with open(self.path) as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def spent_lamports(self) -> int:
        return sum(e["fee_lamports"] for e in self.entries())

    def check_can_spend(self, fee_lamports: int):
        if self.cap_lamports is None:
            raise CapExceeded("fee cap is not set in config — live mode refuses")
        projected = self.spent_lamports() + fee_lamports
        if projected > self.cap_lamports:
            raise CapExceeded(
                f"spend cap would be exceeded: spent {self.spent_lamports()} + "
                f"{fee_lamports} > cap {self.cap_lamports} lamports"
            )

    def record(self, entry: dict):
        with open(self.path, "a") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
