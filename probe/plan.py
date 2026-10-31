"""Probe-set construction for one leader window.

Eleven transactions per window, all dust transfers (1..11 lamports) between
the project's own eight funded accounts (indices 0..7; 0 = main, 1..7 = S1..S7).
The transfer amount is `base + send_seq`, unique per probe within the window:
two probes that shared payer, recipient, price AND amount under one blockhash
would be byte-identical — the same signature — and the second could never
land. The amount is far too small to affect fees or ordering; it is purely a
uniqueness nonce.

  fee ladder (4)      pairs (0->1) (2->3) (4->5) (6->7), pairwise
                      account-disjoint; CU prices ascending from the config
                      ladder; sent cheapest first. A fee-following scheduler
                      lands them in reverse send order; an arrival-following
                      one preserves send order.
  arrival ladder (4)  same four disjoint pairs, all price 0, sent in a rapid
                      burst in a recorded order. Measures whether arrival
                      order survives at all, and its jitter.
  conflict pair (2)   (2->1) price 0 sent first, (3->1) at the top ladder
                      price sent second. Both write account 1, so they must
                      serialise; the pair exposes the rule applied *inside*
                      a conflict chain.
  path control (1)    (7->0) at the mid ladder price, sent via the alternate
                      RPC endpoint. Separates "the scheduler's rule" from
                      "the road to the scheduler" at the RPC level.

Relative landed order within each set is the statistic; absolute latency is
never used. See DESIGN.md for the budget arithmetic and the claims this
sample can and cannot support.
"""

from .txbuild import total_fee_lamports

_FEE_PAIRS = [(0, 1), (2, 3), (4, 5), (6, 7)]
_ARRIVAL_PAIRS = [(0, 1), (2, 3), (4, 5), (6, 7)]


def build_window_plan(cfg, target: dict, window_start: int, window_end: int):
    ladder = cfg.data["fee_ladder_micro_lamports_per_cu"]
    if len(ladder) != 4:
        raise ValueError("fee ladder must have exactly 4 rungs for the account rotation")
    cu_limit = cfg.cu_limit
    items = []

    def add(set_name, rung, payer_idx, recipient_idx, price, path):
        items.append(
            {
                "set": set_name,
                "rung": rung,
                "payer_index": payer_idx,
                "recipient_index": recipient_idx,
                "price_micro_lamports_per_cu": price,
                "path": path,  # "rpc_primary" | "rpc_alt"
                "estimated_fee_lamports": total_fee_lamports(price, cu_limit),
            }
        )

    for rung, ((payer, recip), price) in enumerate(zip(_FEE_PAIRS, ladder)):
        add("fee", rung, payer, recip, price, "rpc_primary")
    for rung, (payer, recip) in enumerate(_ARRIVAL_PAIRS):
        add("arrival", rung, payer, recip, 0, "rpc_primary")
    add("conflict", 0, 2, 1, 0, "rpc_primary")
    add("conflict", 1, 3, 1, cfg.conflict_high_price_micro_lamports_per_cu,
        "rpc_primary")
    add("control", 0, 7, 0, cfg.control_price_micro_lamports_per_cu, "rpc_alt")

    for seq, item in enumerate(items):
        item["send_seq"] = seq
        item["transfer_lamports"] = cfg.transfer_lamports + seq

    return {
        "target_label": target["label"],
        "target_client": target["client"],
        "target_identity": target["identity_pubkey"],
        "target_vote": target["vote_pubkey"],
        "window_start": window_start,
        "window_end": window_end,
        "cu_limit": cu_limit,
        "transfer_lamports_base": cfg.transfer_lamports,
        "items": items,
        "total_estimated_fee_lamports": sum(i["estimated_fee_lamports"] for i in items),
    }


def plan_paths(plan, accounts):
    """Resolve account indices to pubkeys for display/logging."""
    out = []
    for item in plan["items"]:
        row = dict(item)
        row["payer_pubkey"] = accounts[item["payer_index"]].pubkey
        row["recipient_pubkey"] = accounts[item["recipient_index"]].pubkey
        out.append(row)
    return out
