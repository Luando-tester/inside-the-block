"""Campaign teardown — the final sweep DESIGN.md always promised.

DESIGN.md's teardown arithmetic assumes 7 sweep transfers: every sender
float returns to the main account ("every lamport is recoverable by the
final sweep"). The probe CLI never grew a sweep command (see the
"Teardown attempt — HALTED" addendum in reports/READINESS.md), so this
script implements that documented step directly on the project's own
modules (probe/keypair.py, probe/txbuild.py, probe/rpc.py), mirroring
the funding-transfer pattern of probe/sender.py's setup_accounts:
plain transfers built with probe.txbuild at price 0, one signature,
5,000-lamport base fee each.

Two phases, one run, with reconciliation gates between and inside
phases — any mismatch halts the whole teardown immediately, with no
further transfers:

  Phase A (sweep): for each sender S1..S7, read its balance B live;
    if B <= 5,000 skip it (nothing recoverable above the fee);
    otherwise transfer (B - 5,000) to main, wait for finalization,
    then verify the sender reads exactly 0 and main increased by
    exactly (B - 5,000).
  Phase B (return): read main's balance M live; transfer
    (M - rent_exempt_minimum - 5,000) to the operator's personal
    Solana wallet, leaving main at exactly the rent-exempt minimum;
    verify both sides to the lamport.

Keys load only via the PROBE_KEYPAIR_FILE environment variable (the
config's `keypair_env`), exactly as in live mode. Nothing secret is
printed: the output records pubkeys, amounts and signatures only.

Usage:
    PROBE_KEYPAIR_FILE=<path> python3 teardown.py            # full run
    PROBE_KEYPAIR_FILE=<path> python3 teardown.py --snapshot # read-only
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

from probe import config as config_mod
from probe.keypair import KeypairSet
from probe.rpc import RpcClient, RpcError
from probe.txbuild import (BASE_FEE_PER_SIGNATURE_LAMPORTS,
                           build_probe_transaction)

FEE = BASE_FEE_PER_SIGNATURE_LAMPORTS  # 5,000 — the only fee a price-0 transfer pays
OPERATOR_WALLET = "EMCzkUmfVLcbey2eugzppupQkz4Z8FiosLpMP9opUDv1"
CONFIRM_TIMEOUT_S = 180
BALANCE_GRACE_S = 60


class TeardownError(Exception):
    """Raised on any mismatch or RPC failure; carries the exact state."""

    def __init__(self, message, state=None):
        super().__init__(message)
        self.state = state or {}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_keypairs(cfg) -> KeypairSet:
    env_name = cfg.get("keypair_env", "PROBE_KEYPAIR_FILE")
    path = os.environ.get(env_name)
    if not path:
        raise TeardownError(f"{env_name} is not set — refusing to run")
    return KeypairSet.load(path)


def read_balances(rpc: RpcClient, keypairs: KeypairSet) -> dict:
    out = {"main": rpc.get_balance(keypairs.main.pubkey)}
    for idx, sender in enumerate(keypairs.senders, start=1):
        out[f"S{idx}"] = rpc.get_balance(sender.pubkey)
    out["operator"] = rpc.get_balance(OPERATOR_WALLET)
    return out


def pubkeys(keypairs: KeypairSet) -> dict:
    out = {"main": keypairs.main.pubkey}
    for idx, sender in enumerate(keypairs.senders, start=1):
        out[f"S{idx}"] = sender.pubkey
    out["operator"] = OPERATOR_WALLET
    return out


def send_transfer(rpc: RpcClient, cfg, payer, recipient_pubkey: str,
                  amount: int) -> str:
    """One plain transfer, built exactly like sender.setup_accounts'."""
    blockhash = rpc.get_latest_blockhash()
    tx_b64, signature = build_probe_transaction(
        payer, recipient_pubkey, 0, cfg.cu_limit, amount, blockhash
    )
    returned = rpc.send_transaction(tx_b64)
    if returned != signature:
        raise TeardownError(
            f"RPC returned signature {returned}, locally computed "
            f"{signature} — treating as mismatch",
            {"sent_signature": signature, "rpc_signature": returned},
        )
    return signature


def signature_status(rpc: RpcClient, signature: str):
    result = rpc.call(
        "getSignatureStatuses",
        [[signature], {"searchTransactionHistory": True}],
    )
    values = result.get("value") or []
    return values[0] if values else None


def wait_finalized(rpc: RpcClient, signature: str, what: str):
    """Poll until the transaction is finalized; halt on error/timeout."""
    deadline = time.monotonic() + CONFIRM_TIMEOUT_S
    last = None
    while time.monotonic() < deadline:
        last = signature_status(rpc, signature)
        if last is not None:
            if last.get("err") is not None:
                raise TeardownError(
                    f"{what}: transaction {signature} failed on-chain: "
                    f"{last['err']}",
                    {"signature": signature, "status": last},
                )
            if last.get("confirmationStatus") == "finalized":
                return last
        time.sleep(2)
    raise TeardownError(
        f"{what}: transaction {signature} not finalized within "
        f"{CONFIRM_TIMEOUT_S}s (last status: {last})",
        {"signature": signature, "status": last},
    )


def verify_balances(rpc: RpcClient, checks: dict, what: str):
    """Re-read balances until every expected value holds (grace for node
    lag after finalization), else halt with the exact observed state."""
    deadline = time.monotonic() + BALANCE_GRACE_S
    observed = {}
    while True:
        observed = {}
        for label, (pubkey, expected) in checks.items():
            observed[label] = rpc.get_balance(pubkey)
        if all(observed[label] == expected
               for label, (_pk, expected) in checks.items()):
            return observed
        if time.monotonic() >= deadline:
            expected_map = {label: exp for label, (_pk, exp)
                            in checks.items()}
            raise TeardownError(
                f"{what}: balance mismatch after finalization — "
                f"expected {expected_map}, observed {observed}",
                {"expected": expected_map, "observed": observed},
            )
        time.sleep(2)


def main(argv):
    snapshot_only = "--snapshot" in argv
    cfg = config_mod.load()
    rpc = RpcClient(cfg.rpc_url)
    keypairs = load_keypairs(cfg)
    keys = pubkeys(keypairs)
    rent_reserve = cfg.rent_exempt_minimum_lamports

    report = {
        "started": _now_iso(),
        "slot_at_start": rpc.get_slot(),
        "pubkeys": keys,
        "reserve_rent_exempt_lamports": rent_reserve,
        "fee_per_transfer_lamports": FEE,
    }
    before = read_balances(rpc, keypairs)
    report["balances_before"] = before
    print(f"[{report['started']}] slot {report['slot_at_start']}")
    print(f"balances before: {json.dumps(before, sort_keys=True)}")
    if snapshot_only:
        report["snapshot_only"] = True
        print("TEARDOWN_SNAPSHOT_JSON " + json.dumps(report, sort_keys=True))
        return 0

    main_kp = keypairs.main

    # ---------------- Phase A: sweep S1..S7 -> main ----------------
    phase_a = []
    for idx, sender in enumerate(keypairs.senders, start=1):
        label = f"S{idx}"
        balance = rpc.get_balance(sender.pubkey)
        if balance <= FEE:
            phase_a.append({"sender": label, "skipped": True,
                            "balance": balance,
                            "reason": f"balance {balance} <= fee {FEE}"})
            print(f"phase A {label}: SKIP (balance {balance} <= fee {FEE})")
            continue
        main_before = rpc.get_balance(main_kp.pubkey)
        amount = balance - FEE
        signature = send_transfer(rpc, cfg, sender, main_kp.pubkey, amount)
        wait_finalized(rpc, signature, f"phase A {label} sweep")
        observed = verify_balances(
            rpc,
            {label: (sender.pubkey, 0),
             "main": (main_kp.pubkey, main_before + amount)},
            f"phase A {label} sweep",
        )
        entry = {"sender": label, "balance_before": balance,
                 "amount": amount, "signature": signature,
                 "sender_after": observed[label],
                 "main_after": observed["main"]}
        phase_a.append(entry)
        print(f"phase A {label}: swept {amount} (sig {signature}); "
              f"sender=0, main={observed['main']}")
    report["phase_a"] = phase_a
    report["recovered_total"] = sum(e.get("amount", 0) for e in phase_a)
    after_a = read_balances(rpc, keypairs)
    report["balances_after_phase_a"] = after_a
    print(f"phase A complete: recovered {report['recovered_total']}; "
          f"balances: {json.dumps(after_a, sort_keys=True)}")

    # ---------------- Phase B: main -> operator wallet ----------------
    operator_before = rpc.get_balance(OPERATOR_WALLET)
    main_now = rpc.get_balance(main_kp.pubkey)
    amount = main_now - rent_reserve - FEE
    if amount <= 0:
        raise TeardownError(
            f"phase B: nothing returnable — main {main_now}, reserve "
            f"{rent_reserve}, fee {FEE}",
            {"balances": read_balances(rpc, keypairs)},
        )
    signature = send_transfer(rpc, cfg, main_kp, OPERATOR_WALLET, amount)
    wait_finalized(rpc, signature, "phase B return")
    observed = verify_balances(
        rpc,
        {"main": (main_kp.pubkey, rent_reserve),
         "operator": (OPERATOR_WALLET, operator_before + amount)},
        "phase B return",
    )
    report["phase_b"] = {
        "main_before": main_now, "operator_before": operator_before,
        "amount": amount, "signature": signature,
        "main_after": observed["main"], "operator_after": observed["operator"],
    }
    print(f"phase B: returned {amount} (sig {signature}); "
          f"main={observed['main']}, operator={observed['operator']}")

    after = read_balances(rpc, keypairs)
    report["balances_final"] = after
    report["slot_at_end"] = rpc.get_slot()
    report["finished"] = _now_iso()
    print(f"final balances: {json.dumps(after, sort_keys=True)}")
    print("TEARDOWN_RESULT_JSON " + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except TeardownError as exc:
        print(f"TEARDOWN HALTED: {exc}", file=sys.stderr)
        if exc.state:
            print("STATE_JSON " + json.dumps(exc.state, sort_keys=True),
                  file=sys.stderr)
        sys.exit(2)
    except RpcError as exc:
        print(f"TEARDOWN HALTED: RPC error: {exc}", file=sys.stderr)
        sys.exit(2)
