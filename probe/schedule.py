"""Leader-schedule resolution and live client re-verification.

Solana leaders serve consecutive slots (normally 4). A *window* is a maximal
run of slots led by the same identity. Targets are keyed by identity pubkey
(the leader schedule is published per identity, not per vote account).
"""

from .rpc import RpcClient

# Slots per leader rotation — the measurement unit for one window.
WINDOW_SLOTS = 4


def group_windows(slots):
    """Group a sorted slot list into (start, end_inclusive) runs."""
    windows = []
    for slot in slots:
        if windows and slot == windows[-1][1] + 1:
            windows[-1][1] = slot
        else:
            windows.append([slot, slot])
    return [(start, end) for start, end in windows]


def next_windows(rpc: RpcClient, identity_pubkey: str, after_slot: int, count: int = 3):
    """Next `count` leader windows for `identity_pubkey` strictly after
    `after_slot`, looking into the next epoch if needed.

    Note: with an explicit epoch, getLeaderSchedule returns slot indices
    relative to the epoch start; convert to absolute slots here.
    """
    epoch_info = rpc.get_epoch_info()
    slots_in_epoch = epoch_info["slotsInEpoch"]
    found = []
    epoch = epoch_info["epoch"]
    for ep in (epoch, epoch + 1):
        schedule = rpc.get_leader_schedule(ep) or {}
        base = ep * slots_in_epoch
        slots = sorted(base + s for s in schedule.get(identity_pubkey, []))
        # Group into runs FIRST, then cut each run into rotation-sized
        # windows (WINDOW_SLOTS) aligned to the run start, and keep only
        # windows whose FIRST slot is strictly after after_slot:
        # - filtering slots before grouping would return the tail of an
        #   already-started run as a truncated "window" whose start the
        #   analyzer would treat as a separate window;
        # - not cutting at all would make a very long run (a validator
        #   holding consecutive rotations — or a sole local leader) one
        #   giant window, while the measurement unit is one rotation.
        for run_start, run_end in group_windows(slots):
            ws = run_start
            while ws <= run_end:
                window = (ws, min(ws + WINDOW_SLOTS - 1, run_end))
                if window[0] > after_slot:
                    found.append(window)
                    if len(found) >= count:
                        return found
                ws += WINDOW_SLOTS
    return found


def live_client_info(rpc: RpcClient, identity_pubkeys):
    """Re-read gossip clientId + version for the given identities, live."""
    nodes = {n["pubkey"]: n for n in rpc.get_cluster_nodes()}
    out = {}
    for pubkey in identity_pubkeys:
        node = nodes.get(pubkey)
        if node is None:
            out[pubkey] = {"clientId": None, "version": None, "in_gossip": False}
        else:
            out[pubkey] = {
                "clientId": node.get("clientId"),
                "version": node.get("version"),
                "in_gossip": True,
            }
    return out
