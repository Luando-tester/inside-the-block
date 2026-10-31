"""Thin Solana JSON-RPC client (read methods + one gated send method).

Read methods are unrestricted. `send_transaction` exists for the live executor
and is only ever called from sender.py after every safety gate has passed.
"""

import time

import requests


class RpcError(Exception):
    pass


class RpcClient:
    def __init__(self, url: str, timeout: float = 30.0, max_retries: int = 4):
        self.url = url
        self.timeout = timeout
        self.max_retries = max_retries
        self._id = 0
        self._session = requests.Session()

    def call(self, method: str, params=None):
        last_err = None
        for attempt in range(self.max_retries):
            self._id += 1
            payload = {"jsonrpc": "2.0", "id": self._id, "method": method}
            if params is not None:
                payload["params"] = params
            try:
                resp = self._session.post(self.url, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                body = resp.json()
                if "error" in body:
                    raise RpcError(f"{method}: {body['error']}")
                return body["result"]
            except (requests.RequestException, RpcError) as exc:
                last_err = exc
                if attempt < self.max_retries - 1:
                    time.sleep(0.6 * (attempt + 1))
        raise RpcError(f"{method} failed after {self.max_retries} tries: {last_err}")

    # --- read-only -----------------------------------------------------------
    def get_slot(self) -> int:
        return self.call("getSlot")

    def get_epoch_info(self):
        return self.call("getEpochInfo")

    def get_leader_schedule(self, epoch=None):
        params = [{"epoch": epoch}] if epoch is not None else []
        return self.call("getLeaderSchedule", params)

    def get_slot_leaders(self, start_slot: int, limit: int):
        return self.call("getSlotLeaders", [start_slot, limit])

    def get_cluster_nodes(self):
        return self.call("getClusterNodes")

    def get_balance(self, pubkey: str) -> int:
        return self.call("getBalance", [pubkey])["value"]

    def get_latest_blockhash(self):
        return self.call("getLatestBlockhash")["value"]["blockhash"]

    def get_block(self, slot: int):
        return self.call(
            "getBlock",
            [
                slot,
                {
                    "encoding": "json",
                    "transactionDetails": "full",
                    "rewards": False,
                    # Post-Alpenglow blocks contain version-1 transactions;
                    # the RPC refuses the call unless we opt in to them.
                    "maxSupportedTransactionVersion": 1,
                },
            ],
        )

    # --- gated (live executor only) ------------------------------------------
    def send_transaction(self, signed_tx_b64: str) -> str:
        return self.call(
            "sendTransaction",
            [signed_tx_b64, {"encoding": "base64", "skipPreflight": False,
                             "maxRetries": 3}],
        )
