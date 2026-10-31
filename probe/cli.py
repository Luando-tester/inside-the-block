"""Command-line entry point.

Subcommands:
  keygen     generate the project keypair set (refuses to overwrite)
  schedule   READ-ONLY: next leader windows + live client check for targets
  plan       print the probe plan for a target's next window (no sends)
  dry-run    READ-ONLY proof: schedule + client check + fetch & parse one
             recent block, demonstrating position extraction. Sends nothing.
  send       execute probe windows. Dry-run by default; broadcasting needs
             --live AND PROBE_KEYPAIR_FILE AND the config gates in sender.py.
  analyze    locate logged probes in blocks and summarise ordering statistics

Examples:
  python -m probe.cli dry-run
  python -m probe.cli schedule
  PROBE_KEYPAIR_FILE=/path/outside/repo/.probe_keypair.json \
      python -m probe.cli send --live --windows 3
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from . import config as config_mod
from . import plan as plan_mod
from . import schedule as schedule_mod
from . import sender as sender_mod
from .keypair import KeypairSet
from .rpc import RpcClient


def _ts():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _targets(cfg):
    data = config_mod.load_validators(cfg)
    return data["primaries"]


def cmd_keygen(args):
    path = args.out
    if os.path.exists(path):
        print(f"refusing to overwrite existing keypair file: {path}")
        return 1
    keypairs = KeypairSet.generate(n_senders=7)
    keypairs.save(path)
    print(f"wrote keypair set to {path} (chmod 600)")
    print(f"main (funding target): {keypairs.main.pubkey}")
    for i, kp in enumerate(keypairs.senders, start=1):
        print(f"  S{i}: {kp.pubkey}")
    return 0


def cmd_schedule(args):
    cfg = config_mod.load(args.config)
    rpc = RpcClient(cfg.rpc_url)
    slot = rpc.get_slot()
    targets = _targets(cfg)
    infos = schedule_mod.live_client_info(
        rpc, [t["identity_pubkey"] for t in targets])
    print(f"current slot: {slot}")
    for t in targets:
        info = infos[t["identity_pubkey"]]
        windows = schedule_mod.next_windows(
            rpc, t["identity_pubkey"], slot, count=args.windows)
        print(f"\n{t['label']} ({t['client']}, snapshot {t['version']}) "
              f"live: clientId={info['clientId']} version={info['version']}")
        for start, end in windows:
            print(f"  next window: slots {start}..{end} "
                  f"(in ~{(start - slot) * 0.4:.0f}s)")
    return 0


def cmd_plan(args):
    cfg = config_mod.load(args.config)
    rpc = RpcClient(cfg.rpc_url)
    slot = rpc.get_slot()
    target = next(t for t in _targets(cfg) if t["label"] == args.target)
    start, end = schedule_mod.next_windows(
        rpc, target["identity_pubkey"], slot, count=1)[0]
    window_plan = plan_mod.build_window_plan(cfg, target, start, end)
    accounts = KeypairSet.generate()  # display only; pubkeys are placeholders
    print(json.dumps(window_plan, indent=2))
    print(f"accounts needed: {len(accounts.all_accounts())} project accounts; "
          f"total estimated fees: {window_plan['total_estimated_fee_lamports']} "
          "lamports")
    return 0


def cmd_dry_run(args):
    cfg = config_mod.load(args.config)
    rpc = RpcClient(cfg.rpc_url)
    lines = []

    def emit(line=""):
        print(line)
        lines.append(line)

    emit(f"== dry-run {_ts()} (READ-ONLY: nothing is signed or sent) ==")
    epoch = rpc.get_epoch_info()
    slot = epoch["absoluteSlot"]
    emit(f"epoch {epoch['epoch']}  slot {slot}  "
         f"slotIndex {epoch['slotIndex']}/{epoch['slotsInEpoch']}")

    targets = _targets(cfg)
    infos = schedule_mod.live_client_info(
        rpc, [t["identity_pubkey"] for t in targets])
    emit("\ntarget leader windows (next per validator):")
    for t in targets:
        info = infos[t["identity_pubkey"]]
        windows = schedule_mod.next_windows(
            rpc, t["identity_pubkey"], slot, count=2)
        wtxt = ", ".join(f"{s}..{e}" for s, e in windows) or "none this/next epoch"
        emit(f"  {t['label']:22} client={info['clientId']} "
             f"version={info['version']}  windows: {wtxt}")

    demo_slot = slot - 200
    block = rpc.get_block(demo_slot)
    txs = block.get("transactions", []) if block else []
    emit(f"\nblock parse demo: slot {demo_slot} contains {len(txs)} transactions")
    if txs:
        first_sig = txs[0]["transaction"]["signatures"][0]
        found = next(
            i for i, tx in enumerate(txs)
            if tx["transaction"]["signatures"][0] == first_sig)
        emit(f"  position extraction check: signature {first_sig[:16]}... "
             f"located at index {found} of {len(txs)} (expected 0)")
        mid = txs[len(txs) // 2]["transaction"]["signatures"][0]
        emit(f"  middle transaction signature: {mid[:24]}... "
             f"at index {len(txs) // 2}")
    emit("\ndry-run complete: schedule resolution, live client check and "
         "block parsing all work against public mainnet RPC. No transaction "
         "was built for broadcast and nothing was sent.")

    os.makedirs(cfg.data_dir_path(), exist_ok=True)
    log_path = os.path.join(cfg.data_dir_path(), f"dry_run_{_ts()}.log")
    with open(log_path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\nlog written to {log_path}")
    return 0


def cmd_send(args):
    cfg = config_mod.load(args.config)
    rpc = RpcClient(cfg.rpc_url)
    rpc_alt = RpcClient(cfg.rpc_url_alt)
    targets = _targets(cfg)
    if args.target:
        targets = [t for t in targets if t["label"] == args.target]

    if not args.live:
        # Build-and-sign proof with throwaway keys: constructs every window
        # plan's transactions, broadcasts nothing, writes no ledger.
        print("send without --live: building transactions with ephemeral "
              "keys only; nothing will be broadcast.")
        keypairs = KeypairSet.generate()
        slot = rpc.get_slot()
        for t in targets:
            start, end = schedule_mod.next_windows(
                rpc, t["identity_pubkey"], slot, count=1)[0]
            wp = plan_mod.build_window_plan(cfg, t, start, end)
            records = sender_mod.execute_window(
                cfg, rpc, rpc_alt, keypairs, wp, ledger=None, live=False)
            print(f"  {t['label']}: built {len(records)} probe transactions "
                  f"for window {start}..{end} (not sent)")
        return 0

    keypairs = sender_mod.load_live_keypairs(cfg)
    slot = rpc.get_slot()
    # Minimum planning lead: never plan a window that starts sooner than
    # this many slots from now, so setup, blockhash prefetch and burst
    # building always have room (a window that starts before its burst is
    # ready can only be skipped, wasting the plan). ~30 s at 400 ms slots.
    lead = int(cfg.get("min_window_lead_slots", 75))
    plans = []
    total_fees = 0
    for t in targets:
        windows = schedule_mod.next_windows(
            rpc, t["identity_pubkey"], slot + lead, count=args.windows)
        for start, end in windows:
            wp = plan_mod.build_window_plan(cfg, t, start, end)
            plans.append(wp)
            total_fees += wp["total_estimated_fee_lamports"]
    # Execute in time order across all targets: leader windows of different
    # validators interleave, so a per-target loop would let later targets'
    # windows pass while earlier ones are still firing. A window whose start
    # has already passed when its turn comes is SKIPPED — its probes would
    # land in another leader's block and burn fees for no evidence.
    plans.sort(key=lambda p: p["window_start"])
    ledger = sender_mod.check_live_preconditions(cfg, rpc, keypairs, total_fees)
    print(f"live campaign: {len(plans)} windows, planned fees "
          f"{total_fees} lamports, cap {cfg.fee_cap_lamports}")
    setup_done = set()
    for wp in plans:
        if rpc.get_slot() >= wp["window_start"]:
            print(f"  {wp['target_label']} window {wp['window_start']}: "
                  "SKIPPED (window already started or passed)")
            continue
        if wp["target_label"] not in setup_done:
            # Refresh sender top-ups before this validator's windows. The
            # heaviest account draws ~15k lamports of fees per window; the
            # top-up float is sized per validator cycle (see DESIGN.md),
            # and setup is idempotent — it only sends what is missing.
            sender_mod.setup_accounts(cfg, rpc, keypairs, ledger)
            setup_done.add(wp["target_label"])
        records = sender_mod.execute_window(
            cfg, rpc, rpc_alt, keypairs, wp, ledger=ledger, live=True)
        sent = sum(1 for r in records if r["status"] == "sent")
        print(f"  {wp['target_label']} window {wp['window_start']}: "
              f"{sent}/{len(records)} sent")
    return 0


def cmd_analyze(args):
    from . import analyzer

    cfg = config_mod.load(args.config)
    rpc = RpcClient(cfg.rpc_url)
    records = [r for r in analyzer.load_send_log(cfg.data_dir_path())
               if r.get("mode") == "live" and r.get("status") == "sent"]
    if not records:
        print("no live send records found in the send log — nothing to analyse")
        return 0
    records = analyzer.locate_probes(rpc, records)
    summary = analyzer.summarize(records)
    out = {"generated": _ts(), "summary": summary, "records": records}
    out_path = os.path.join(cfg.data_dir_path(), f"analysis_{_ts()}.json")
    with open(out_path, "w") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps(summary, indent=2))
    print(f"\nfull analysis written to {out_path}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="probe")
    parser.add_argument("--config", default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("keygen")
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_keygen)

    p = sub.add_parser("schedule")
    p.add_argument("--windows", type=int, default=3)
    p.set_defaults(fn=cmd_schedule)

    p = sub.add_parser("plan")
    p.add_argument("--target", required=True)
    p.set_defaults(fn=cmd_plan)

    p = sub.add_parser("dry-run")
    p.set_defaults(fn=cmd_dry_run)

    p = sub.add_parser("send")
    p.add_argument("--live", action="store_true")
    p.add_argument("--target", default=None)
    p.add_argument("--windows", type=int, default=3)
    p.set_defaults(fn=cmd_send)

    p = sub.add_parser("analyze")
    p.set_defaults(fn=cmd_analyze)

    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except (sender_mod.LiveRefused, sender_mod.CapExceeded) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
