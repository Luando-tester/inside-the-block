"""Live probe executor — the only module that can broadcast transactions.

Safety gates, all mandatory, no overrides:
  1. The caller must pass live=True (the CLI requires the --live flag).
  2. A keypair set must be supplied via the PROBE_KEYPAIR_FILE environment
     variable (config key `keypair_env`). Keys never come from the repo.
  3. The config fee cap must be set; the spend ledger refuses any send that
     would push cumulative fees past it (see ledger.py).
  4. Before the first send of a campaign, the main wallet balance must cover
     the configured minimum (funding for the sender top-ups + campaign fees).
  5. Every send is written to the spend ledger and the send log, whether it
     succeeds, fails preflight, or never lands.

One-time account setup (`setup_accounts`) tops each sender up to
rent-exempt minimum + a spend float, from the main account. These funding
transfers are ordinary signed transfers from the project wallet and are
ledger-recorded like everything else. The matching sweep is an operator
action at campaign end (documented in the README), not automated here.
"""

import json
import os
import time
from datetime import datetime, timezone

from . import plan as plan_mod
from .keypair import KeypairSet
from .ledger import CapExceeded, SpendLedger
from .rpc import RpcClient, RpcError
from .txbuild import (BASE_FEE_PER_SIGNATURE_LAMPORTS, build_probe_transaction,
                      total_fee_lamports)

# A Solana blockhash stays valid for ~150 slots after the block it was taken
# from. execute_window fetches blockhashes BEFORE the window wait; if a
# path's blockhash has aged past this many slots by burst time, it is
# re-fetched once and that path's transactions are re-signed before firing.
# 100 leaves a ~50-slot safety margin under the validity limit.
BLOCKHASH_MAX_AGE_SLOTS = 100


class LiveRefused(Exception):
    pass


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_live_keypairs(cfg) -> KeypairSet:
    env_name = cfg.get("keypair_env", "PROBE_KEYPAIR_FILE")
    path = os.environ.get(env_name)
    if not path:
        raise LiveRefused(
            f"{env_name} is not set — live mode needs a keypair file supplied "
            "via the environment; keys are never read from the repository"
        )
    return KeypairSet.load(path)


def check_live_preconditions(cfg, rpc: RpcClient, keypairs: KeypairSet,
                             planned_fee_lamports: int):
    if cfg.fee_cap_lamports is None:
        raise LiveRefused("config fee_cap_lamports is unset — refusing live mode")
    ledger = SpendLedger(cfg.data_dir_path(), cfg.fee_cap_lamports)
    ledger.check_can_spend(planned_fee_lamports)  # raises CapExceeded
    balance = rpc.get_balance(keypairs.main.pubkey)
    minimum = cfg.get("min_wallet_balance_lamports", 0)
    if balance < minimum:
        raise LiveRefused(
            f"main wallet balance {balance} lamports < required minimum "
            f"{minimum} — fund the probe wallet before running live"
        )
    return ledger


def setup_accounts(cfg, rpc: RpcClient, keypairs: KeypairSet, ledger: SpendLedger):
    """Top up each sender to rent-exempt minimum + float, from main."""
    rent = cfg.rent_exempt_minimum_lamports
    topup = cfg.sender_topup_lamports
    target = rent + topup
    log_path = os.path.join(cfg.data_dir_path(), "send_log.jsonl")
    for idx, sender in enumerate(keypairs.senders, start=1):
        balance = rpc.get_balance(sender.pubkey)
        if balance >= target:
            continue
        amount = target - balance
        fee = BASE_FEE_PER_SIGNATURE_LAMPORTS
        ledger.check_can_spend(fee)
        blockhash = rpc.get_latest_blockhash()
        # Funding transfers reuse the probe builder with price 0 and the
        # transfer amount set to the top-up amount.
        tx_b64, signature = build_probe_transaction(
            keypairs.main, sender.pubkey, 0, cfg.cu_limit, amount, blockhash
        )
        entry = {
            "ts": _now_iso(), "kind": "funding", "signature": signature,
            "payer_pubkey": keypairs.main.pubkey, "recipient_pubkey": sender.pubkey,
            "lamports": amount, "fee_lamports": fee, "status": "attempted",
        }
        ledger.record(entry)
        try:
            rpc.send_transaction(tx_b64)
            entry["status"] = "sent"
        except RpcError as exc:
            entry["status"] = f"error: {exc}"
            with open(log_path, "a") as fh:
                fh.write(json.dumps(entry, sort_keys=True) + "\n")
            raise
        with open(log_path, "a") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")


def execute_window(cfg, rpc: RpcClient, rpc_alt: RpcClient, keypairs: KeypairSet,
                   window_plan: dict, ledger: SpendLedger, live: bool = False):
    """Fire one window's probe set at its leader window.

    Order of operations is deliberate: (1) fetch ONE blockhash per RPC path
    and build + sign every transaction up front; (2) when live, wait until
    the window is about to open (slot >= window_start - 2); (2b) check
    blockhash freshness and re-sign any path whose blockhash has aged out
    (below); (3) burst immediately — the only network calls inside the burst
    are the sends themselves, separated by the configured gaps. Building
    BEFORE the wait is a fix from run 1 (2026-10-31): the original order
    waited first and fetched the blockhashes afterwards, and those two
    public-RPC round-trips of latency after the wait pushed the whole burst
    several slots late — only 10 of 176 probes landed inside their target
    windows, and outside landings sat a median of 5 slots after window end.

    Building first has one hazard, measured in run 2 (2026-10-31): a
    blockhash stays valid for only ~150 slots, and the executor builds a
    window's burst when that window's turn comes — for a later-queued
    window whose start is far ahead, the wait itself can carry the burst
    more than 150 slots past the build. In run 2 all 44 probes in four
    windows (p2p_org 463500264 and 463500740, kiln1 463501236,
    coinbase04_harmonic 463502600) reached the burst with an expired
    blockhash, failed simulation with BlockhashNotFound (RPC -32002) after
    4 tries each and were never broadcast (no fees charged on-chain). The
    freshness rule in step (2b) closes the hazard: the build records the
    chain slot at which each path's blockhash was fetched, and at burst
    time any path whose blockhash has aged past BLOCKHASH_MAX_AGE_SLOTS
    (100 — a safety margin under the ~150-slot validity) is re-fetched
    ONCE and that path's transactions are re-signed with it (re-signing is
    local CPU work via build_probe_transaction). Paths still fresh fire
    exactly as built. Fetching a fresh blockhash per transaction (the
    naive approach) would put eleven RPC read round-trips of latency
    inside a ~1.6-second window and sprawl the set across other leaders'
    blocks.

    With live=False this is a pure dry-run: transactions are built and signed
    (proving the build path) but never broadcast, and nothing is written to
    the spend ledger. Returns a list of per-send records.
    """
    accounts = keypairs.all_accounts()
    records = []
    send_log_path = os.path.join(cfg.data_dir_path(), "send_log.jsonl")
    gaps = cfg.data.get("send_gap_seconds", {})

    # (1) Build + sign everything, one blockhash per RPC path — BEFORE the
    # wait, so no RPC round-trip latency sits between the wait trigger and
    # the burst (run-1 flaw: fetch-after-wait pushed bursts ~5 slots late).
    # Also record, per path, the chain slot at which its blockhash was
    # fetched: the freshness check at burst time (step 2b) ages each
    # blockhash against this slot. One extra get_slot read per path; build
    # time is not latency-critical.
    path_clients = {"rpc_primary": rpc, "rpc_alt": rpc_alt}
    blockhashes = {}
    blockhash_slots = {}
    for path, client in path_clients.items():
        blockhashes[path] = client.get_latest_blockhash()
        blockhash_slots[path] = client.get_slot()
    built = []
    for item in window_plan["items"]:
        payer = accounts[item["payer_index"]]
        recipient = accounts[item["recipient_index"]]
        client = rpc_alt if item["path"] == "rpc_alt" else rpc
        tx_b64, signature = build_probe_transaction(
            payer, recipient.pubkey, item["price_micro_lamports_per_cu"],
            cfg.cu_limit, item["transfer_lamports"], blockhashes[item["path"]],
        )
        built.append((item, payer, recipient, client, tx_b64, signature))

    # (2) Wait until just before the window when live; dry-run never waits.
    if live:
        start = window_plan["window_start"]
        while rpc.get_slot() < start - 2:
            time.sleep(0.15)

    # (2b) Blockhash freshness (see docstring): for each path whose upfront
    # blockhash has aged past BLOCKHASH_MAX_AGE_SLOTS during the wait,
    # re-fetch that path's blockhash ONCE and re-sign just that path's
    # transactions with it. A still-fresh path fires exactly as built.
    for path, client in path_clients.items():
        if client.get_slot() - blockhash_slots[path] <= BLOCKHASH_MAX_AGE_SLOTS:
            continue
        blockhashes[path] = client.get_latest_blockhash()
        refreshed = []
        for item, payer, recipient, item_client, tx_b64, signature in built:
            if item["path"] == path:
                tx_b64, signature = build_probe_transaction(
                    payer, recipient.pubkey,
                    item["price_micro_lamports_per_cu"], cfg.cu_limit,
                    item["transfer_lamports"], blockhashes[path])
            refreshed.append((item, payer, recipient, item_client,
                              tx_b64, signature))
        built = refreshed

    # (3) Burst.
    burst_t0 = time.monotonic()
    for item, payer, recipient, client, tx_b64, signature in built:
        record = {
            "ts": _now_iso(),
            "mode": "live" if live else "dry_run",
            "signature": signature,
            "target_label": window_plan["target_label"],
            "target_client": window_plan["target_client"],
            "target_identity": window_plan["target_identity"],
            "window_start": window_plan["window_start"],
            "window_end": window_plan["window_end"],
            "set": item["set"],
            "rung": item["rung"],
            "send_seq": item["send_seq"],
            "price_micro_lamports_per_cu": item["price_micro_lamports_per_cu"],
            "payer_pubkey": payer.pubkey,
            "recipient_pubkey": recipient.pubkey,
            "path": item["path"],
            "transfer_lamports": item["transfer_lamports"],
            "fee_lamports": item["estimated_fee_lamports"],
            "status": "built_not_sent",
        }
        if live:
            ledger.check_can_spend(item["estimated_fee_lamports"])
            ledger.record({k: record[k] for k in
                           ("ts", "signature", "fee_lamports", "set",
                            "target_label", "window_start")} |
                          {"kind": "probe", "status": "attempted"})
            try:
                client.send_transaction(tx_b64)
                record["status"] = "sent"
            except RpcError as exc:
                record["status"] = f"error: {exc}"
            record["burst_offset_s"] = round(time.monotonic() - burst_t0, 4)
            with open(send_log_path, "a") as fh:
                fh.write(json.dumps(record, sort_keys=True) + "\n")
            gap_key = {"fee": "fee_ladder", "arrival": "arrival_ladder",
                       "conflict": "conflict_pair"}.get(item["set"], "between_sets")
            time.sleep(gaps.get(gap_key, 0.05))
        records.append(record)
    return records
