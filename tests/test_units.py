"""Unit tests for the probe's pure components. Run: python -m tests.test_units
(or pytest). No network access is used."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from probe import ed25519, plan as plan_mod, stats  # noqa: E402
from probe.base58 import b58decode, b58encode  # noqa: E402
from probe.config import Config  # noqa: E402
from probe.keypair import Keypair, KeypairSet  # noqa: E402
from probe.ledger import CapExceeded, SpendLedger  # noqa: E402
from probe.txbuild import total_fee_lamports  # noqa: E402


def test_ed25519_rfc8032_vector():
    seed = bytes.fromhex(
        "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
    pub = ed25519.public_key_from_seed(seed)
    assert pub.hex() == (
        "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"), pub.hex()
    sig = ed25519.sign(seed, b"")
    assert sig.hex() == (
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
        "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"), sig.hex()


def test_base58():
    assert b58encode(b"") == ""
    assert b58encode(b"hello world") == "StV1DL6CwTryKyV"
    assert b58encode(bytes(32)) == "1" * 32
    assert b58decode("StV1DL6CwTryKyV") == b"hello world"
    assert b58decode(b58encode(bytes(range(32)))) == bytes(range(32))


def test_fee_math():
    assert total_fee_lamports(0, 1000) == 5000
    assert total_fee_lamports(10_000, 1000) == 5010
    assert total_fee_lamports(250_000, 1000) == 5250


def test_stats():
    assert abs(stats.spearman([1, 2, 3, 4], [1, 2, 3, 4]) - 1.0) < 1e-9
    assert abs(stats.spearman([1, 2, 3, 4], [4, 3, 2, 1]) + 1.0) < 1e-9
    assert abs(stats.kendall_tau_b([1, 2, 3, 4], [1, 2, 3, 4]) - 1.0) < 1e-9
    assert abs(stats.kendall_tau_b([1, 2, 3, 4], [4, 3, 2, 1]) + 1.0) < 1e-9


def test_ledger_cap():
    with tempfile.TemporaryDirectory() as td:
        ledger = SpendLedger(td, cap_lamports=10_000)
        ledger.record({"fee_lamports": 6000})
        ledger.check_can_spend(4000)
        try:
            ledger.check_can_spend(4001)
        except CapExceeded:
            pass
        else:
            raise AssertionError("cap was not enforced")
    with tempfile.TemporaryDirectory() as td:
        ledger = SpendLedger(td, cap_lamports=None)
        try:
            ledger.check_can_spend(1)
        except CapExceeded:
            pass
        else:
            raise AssertionError("unset cap must refuse")


def _example_cfg():
    return Config({
        "fee_cap_lamports": 10_000_000,
        "cu_limit": 1000,
        "transfer_lamports": 1,
        "fee_ladder_micro_lamports_per_cu": [0, 10_000, 50_000, 250_000],
        "conflict_high_price_micro_lamports_per_cu": 250_000,
        "control_price_micro_lamports_per_cu": 10_000,
        "data_dir": "data",
        "validators_file": "validators.json",
    })


def test_window_plan_budget_and_disjointness():
    cfg = _example_cfg()
    target = {"label": "t", "client": "c", "identity_pubkey": "id",
              "vote_pubkey": "v"}
    wp = plan_mod.build_window_plan(cfg, target, 100, 103)
    assert len(wp["items"]) == 11, len(wp["items"])
    assert wp["total_estimated_fee_lamports"] == 55_570, wp[
        "total_estimated_fee_lamports"]
    # fee ladder + arrival ladder pairs are internally account-disjoint
    for set_name in ("fee", "arrival"):
        used = []
        for item in wp["items"]:
            if item["set"] == set_name:
                used += [item["payer_index"], item["recipient_index"]]
        assert len(used) == len(set(used)), (set_name, used)
    # campaign arithmetic: 18 windows * 55,570 = 1,000,260 lamports
    assert 18 * wp["total_estimated_fee_lamports"] == 1_000_260


def test_next_windows_epoch_relative():
    from probe import schedule as schedule_mod

    class FakeRpc:
        def get_epoch_info(self):
            return {"epoch": 10, "slotsInEpoch": 100, "absoluteSlot": 1050}

        def get_leader_schedule(self, epoch=None):
            if epoch == 10:
                return {"ID": [60, 61, 62, 63, 90]}
            return {"ID": [0, 1, 2, 3]}

    wins = schedule_mod.next_windows(FakeRpc(), "ID", after_slot=1050, count=2)
    assert wins == [(1060, 1063), (1090, 1090)], wins


def test_next_windows_never_returns_started_window():
    """The live planner passes after_slot = current + lead; a window whose
    slots have already begun must never be returned (its burst could not
    be built and prefetched in time)."""
    from probe import schedule as schedule_mod

    class FakeRpc:
        def get_epoch_info(self):
            return {"epoch": 10, "slotsInEpoch": 100, "absoluteSlot": 1050}

        def get_leader_schedule(self, epoch=None):
            if epoch == 10:
                return {"ID": [60, 61, 62, 63, 90]}
            return {"ID": [0, 1, 2, 3]}

    # after_slot inside window 1060..1063: that window is gone entirely
    wins = schedule_mod.next_windows(FakeRpc(), "ID", after_slot=1061, count=1)
    assert wins == [(1090, 1090)], wins
    # after_slot at a window's first slot: also gone (strictly after)
    wins = schedule_mod.next_windows(FakeRpc(), "ID", after_slot=1090, count=1)
    assert wins == [(1100, 1103)], wins


def test_next_windows_cuts_long_runs_into_rotations():
    """A run longer than one rotation (consecutive rotations by one
    validator — or a sole local leader) is cut into 4-slot windows
    aligned to the run start; the window unit is one rotation."""
    from probe import schedule as schedule_mod

    class FakeRpc:
        def get_epoch_info(self):
            return {"epoch": 0, "slotsInEpoch": 1000, "absoluteSlot": 0}

        def get_leader_schedule(self, epoch=None):
            return {"ID": list(range(100, 112))} if epoch == 0 else {}

    wins = schedule_mod.next_windows(FakeRpc(), "ID", after_slot=50, count=3)
    assert wins == [(100, 103), (104, 107), (108, 111)], wins
    # a lead landing inside the run skips only the started rotations
    wins = schedule_mod.next_windows(FakeRpc(), "ID", after_slot=105, count=2)
    assert wins == [(108, 111)], wins


def test_keypair_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "kp.json")
        kps = KeypairSet.generate(n_senders=7)
        kps.save(path)
        assert oct(os.stat(path).st_mode & 0o777) == "0o600"
        loaded = KeypairSet.load(path)
        assert loaded.main.pubkey == kps.main.pubkey
        assert len(loaded.all_accounts()) == 8
        kp = Keypair(kps.main.seed)
        assert kp.sign(b"x") == kps.main.sign(b"x")


def _landed_record(set_name, rung, send_seq, price, slot, index,
                   window_start=100):
    return {
        "target_label": "t", "target_client": "c", "set": set_name,
        "rung": rung, "send_seq": send_seq,
        "price_micro_lamports_per_cu": price,
        "signature": f"sig-{window_start}-{set_name}-{rung}",
        "window_start": window_start, "window_end": window_start + 3,
        "landed": True, "landed_in_window": True,
        "landed_slot": slot, "landed_index": index,
    }


def test_analyzer_orders_by_slot_then_index():
    from probe import analyzer

    # Fee probe A (price 0) lands at slot 100 index 500; fee probe B (price
    # 250k) lands at slot 101 index 3. Raw index alone would rank B first and
    # fake a fee-following signal; (slot, index) order ranks A first, so the
    # price-vs-position correlation must come out +1 (arrival-like), not -1.
    recs = [
        _landed_record("fee", 0, 0, 0, slot=100, index=500),
        _landed_record("fee", 3, 3, 250_000, slot=101, index=3),
    ]
    summary = analyzer.summarize(recs)
    assert summary[0]["fee_set"]["spearman_price_vs_position"] == 1.0, summary


def test_analyzer_per_window_breakdown():
    from probe import analyzer

    recs = []
    for window in (100, 200):
        for rung, price in enumerate((0, 10_000, 50_000, 250_000)):
            # fee-following within each window: higher price -> earlier slot
            recs.append(_landed_record(
                "fee", rung, rung, price,
                slot=window + (3 - rung), index=10, window_start=window))
    summary = analyzer.summarize(recs)
    per_window = summary[0]["fee_set"]["per_window"]
    assert [w["window_start"] for w in per_window] == [100, 200], per_window
    assert all(w["spearman"] == -1.0 for w in per_window), per_window
    assert summary[0]["fee_set"]["spearman_price_vs_position"] == -1.0


def test_execute_window_burst_builds_with_one_blockhash_per_path():
    from probe import sender as sender_mod

    class FakeRpc:
        def __init__(self):
            self.blockhash_calls = 0

        def get_latest_blockhash(self):
            self.blockhash_calls += 1
            return "11111111111111111111111111111111"

        def get_slot(self):
            return 0

    cfg = _example_cfg()
    target = {"label": "t", "client": "c", "identity_pubkey": "id",
              "vote_pubkey": "v"}
    wp = plan_mod.build_window_plan(cfg, target, 100, 103)
    rpc_a, rpc_b = FakeRpc(), FakeRpc()
    records = sender_mod.execute_window(
        cfg, rpc_a, rpc_b, KeypairSet.generate(), wp, ledger=None, live=False)
    assert len(records) == 11
    assert all(r["status"] == "built_not_sent" for r in records)
    assert len({r["signature"] for r in records}) == 11
    # one blockhash fetch per RPC path for the whole burst — not one per tx
    assert rpc_a.blockhash_calls == 1 and rpc_b.blockhash_calls == 1, (
        rpc_a.blockhash_calls, rpc_b.blockhash_calls)


def test_account_draw_within_float_per_cycle():
    cfg = _example_cfg()
    target = {"label": "t", "client": "c", "identity_pubkey": "id",
              "vote_pubkey": "v"}
    wp = plan_mod.build_window_plan(cfg, target, 100, 103)
    per_account = {}
    for item in wp["items"]:
        per_account[item["payer_index"]] = (
            per_account.get(item["payer_index"], 0)
            + item["estimated_fee_lamports"])
    # 3 windows = one validator cycle; float per sender is 200,000 lamports
    assert all(3 * fees <= 200_000 for fees in per_account.values()), per_account
    assert per_account[2] == 15_010, per_account  # S2 is the heaviest payer


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"{len(fns)} tests passed")
