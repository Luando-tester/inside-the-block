"""Read-back analysis: from send log + blocks to per-validator ordering rules.

For every logged probe signature we fetch the block of its window slots and
record the landed position (slot, and index inside that block's transaction
list) or that it never landed. Landed order is the lexicographic
(slot, index) order — an index alone is meaningless across the different
blocks of a window. Per validator and set we then correlate the intended
order (fee, send order) with the landed order, using within-window landed
ranks so windows pool without comparing raw indices across blocks:

  fee set      spearman(price, landed_position): strongly negative =>
               fee-following (higher price lands earlier). spearman(send_seq,
               landed_position) strongly positive => arrival-following.
  arrival set  spearman(send_seq, landed_position): high positive + tight
               spread => arrival order survives; near zero => it does not.
  conflict     which member of each pair landed first (fee or arrival).

All statistics are descriptive of OUR probes only; other transactions in the
blocks are context, never evidence.
"""

import json
import os
from collections import defaultdict

from .rpc import RpcClient
from .stats import kendall_tau_b, spearman


def load_send_log(data_dir: str):
    path = os.path.join(data_dir, "send_log.jsonl")
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def locate_probes(rpc: RpcClient, records):
    """Annotate each probe record with landed_slot / landed_index (or None).

    Blocks are searched across the target window plus the 8 following slots:
    a probe that misses its window lands in a *different* leader's block and
    must not be credited to the target's ordering rule, so each record also
    gets `landed_in_window`. Only in-window landings feed the statistics.
    """
    slots = sorted({s for r in records
                    for s in range(r["window_start"], r["window_end"] + 9)})
    wanted = {r["signature"] for r in records if r["set"] != "funding"}
    positions = {}
    for slot in slots:
        block = rpc.get_block(slot)
        if not block:
            continue
        for idx, tx in enumerate(block.get("transactions", [])):
            sigs = tx.get("transaction", {}).get("signatures", [])
            if sigs and sigs[0] in wanted:
                positions[sigs[0]] = {"slot": slot, "index": idx,
                                      "block_tx_count": len(block["transactions"])}
    for record in records:
        pos = positions.get(record["signature"])
        record["landed"] = pos is not None
        record["landed_slot"] = pos["slot"] if pos else None
        record["landed_index"] = pos["index"] if pos else None
        record["landed_in_window"] = bool(
            pos and record["window_start"] <= pos["slot"] <= record["window_end"]
        )
    return records


def _safe(fn, xs, ys):
    try:
        return round(fn(xs, ys), 4)
    except ValueError:
        return None


def _order_key(record):
    """Landed order inside a window: block slot first, then index in block."""
    return (record["landed_slot"], record["landed_index"])


def _window_ranks(landed):
    """Annotate in-window landed records with `landed_rank` — the rank of the
    record within its (window, set) group under landed order, 1-based.
    Pooling these ranks across windows is what makes the per-validator and
    per-client statistics meaningful."""
    groups = defaultdict(list)
    for r in landed:
        groups[(r["window_start"], r["set"])].append(r)
    for group in groups.values():
        for rank, r in enumerate(sorted(group, key=_order_key), start=1):
            r["landed_rank"] = rank


def _set_stats(landed, set_name, value_key):
    """Pooled + per-window Spearman of `value_key` against landed rank."""
    recs = [r for r in landed if r["set"] == set_name]
    by_window = defaultdict(list)
    for r in recs:
        by_window[r["window_start"]].append(r)
    per_window = []
    for window, group in sorted(by_window.items()):
        if len(group) >= 2:
            per_window.append({
                "window_start": window,
                "n": len(group),
                "spearman": _safe(spearman, [r[value_key] for r in group],
                                  [r["landed_rank"] for r in group]),
            })
    return recs, per_window


def summarize(records):
    by_target = defaultdict(list)
    for r in records:
        if r.get("kind") == "funding" or r["set"] == "funding":
            continue
        by_target[(r["target_label"], r["target_client"])].append(r)

    summary = []
    for (label, client), recs in sorted(by_target.items()):
        landed = [r for r in recs if r.get("landed_in_window")]
        _window_ranks(landed)
        fee, fee_per_window = _set_stats(landed, "fee",
                                         "price_micro_lamports_per_cu")
        arr, arr_per_window = _set_stats(landed, "arrival", "send_seq")
        conf = defaultdict(dict)
        for r in landed:
            if r["set"] == "conflict":
                conf[(r["window_start"])][r["rung"]] = r
        conflict_outcomes = []
        for window, pair in sorted(conf.items()):
            if 0 in pair and 1 in pair:
                first = 0 if _order_key(pair[0]) < _order_key(pair[1]) else 1
                conflict_outcomes.append(
                    {"window_start": window,
                     "first_landed": "zero_fee_sent_first" if first == 0
                     else "high_fee_sent_second"})
        summary.append(
            {
                "target": label,
                "client": client,
                "probes_sent": len(recs),
                "probes_landed_in_window": len(landed),
                "probes_landed_outside_window": sum(
                    1 for r in recs if r["landed"] and not r["landed_in_window"]),
                "probes_never_landed": sum(1 for r in recs if not r["landed"]),
                "fee_set": {
                    "n": len(fee),
                    "spearman_price_vs_position": _safe(
                        spearman, [r["price_micro_lamports_per_cu"] for r in fee],
                        [r["landed_rank"] for r in fee]),
                    "spearman_sendorder_vs_position": _safe(
                        spearman, [r["send_seq"] for r in fee],
                        [r["landed_rank"] for r in fee]),
                    "kendall_price_vs_position": _safe(
                        kendall_tau_b,
                        [r["price_micro_lamports_per_cu"] for r in fee],
                        [r["landed_rank"] for r in fee]),
                    "per_window": fee_per_window,
                },
                "arrival_set": {
                    "n": len(arr),
                    "spearman_sendorder_vs_position": _safe(
                        spearman, [r["send_seq"] for r in arr],
                        [r["landed_rank"] for r in arr]),
                    "per_window": arr_per_window,
                },
                "conflict_pairs": conflict_outcomes,
            }
        )
    return summary
