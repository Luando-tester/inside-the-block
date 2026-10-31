# Inside the Block — how Solana validators order transactions

A reproducible measurement of the transaction-ordering rule inside production
Solana blocks. We send controlled probe transactions into the leader windows of
**six mainnet validators running three distinct client implementations**
(Jito-Solana, Firedancer, Harmonic's Agave fork), read the landed order back
from the produced blocks, and report — per validator — whether ordering follows
fee-per-compute-unit, arrival order, or no stable rule at probe scale.

Prepared for the Superteam Earn bounty *"Inside the Block: How Solana
Validators Order Transactions"* (Superteam Ukraine). All measurements are on
Solana **Mainnet**, after the Alpenglow upgrade (2026-10-21); none are pooled
across that boundary. Primary evidence is exclusively transactions we send
ourselves; every signature and slot is shipped in `data/` so any judge can
re-run the same `getBlock` checks.

## Run it (one command)

```bash
docker compose run --rm probe dry-run
```

This is a **dry run**: it resolves the targets' upcoming leader windows from
the live schedule, re-reads each target's client from gossip, fetches a recent
block and demonstrates transaction-position extraction. It sends nothing and
needs no keys.

The live campaign (only ever run deliberately, with a funded probe wallet).
Copy the keypair file into `./keys/` (gitignored, mounted read-only into the
container, never baked into the image — see `.dockerignore`), then:

```bash
PROBE_KEYPAIR_FILE=/keys/.probe_keypair.json \
  docker compose run --rm probe send --live --windows 3
PROBE_KEYPAIR_FILE=/keys/.probe_keypair.json \
  docker compose run --rm probe analyze
```

A single `send --live` plans every target's next windows and executes them
in time order (windows whose start has passed are skipped, never fired
late). For the spread-across-days cadence of `DESIGN.md`, run per validator
and occasion instead, e.g. `send --live --target kiln1 --windows 1`.

Without Docker: `pip install -r requirements.txt`, then
`python -m probe.cli <subcommand>` with the same arguments.

## Safety design

- **Dry-run by default.** Broadcasting requires the explicit `--live` flag.
- **Keys only via environment.** The sender loads keypairs solely from the
  file named by `PROBE_KEYPAIR_FILE`. No key material exists in this repo
  (see `.gitignore`); the report and logs contain only public keys.
- **Code-enforced spend cap.** `fee_cap_lamports` in the config (shipped:
  10,000,000 lamports = 0.01 SOL) bounds *cumulative* fees. The spend ledger
  (`probe/ledger.py`) counts every attempted send — failed transactions still
  pay fees — and refuses any send that would cross the cap. There is no
  override. If the cap key is missing from the config, live mode refuses to
  start.
- **Balance gate.** Live mode refuses to start unless the probe wallet holds
  at least `min_wallet_balance_lamports`.
- **Everything is logged.** Every attempted send is written to
  `data/spend_ledger.jsonl` and `data/send_log.jsonl` before/after broadcast.

## Why this design (the considerations the brief asks about)

**Leader schedule and leader types.** The leader schedule is published an
epoch ahead; leaders serve runs of consecutive slots (normally 4). We target
whole runs ("windows") of six pre-identified validators — two each on
Jito-Solana (an Agave fork whose block-engine ecosystem surrounds the
scheduler), Firedancer (an independent C implementation with its own *pack*
scheduler), and HarmonicAgave (a performance fork of Agave). Targets are in
`validators.json` with vote/identity pubkeys, stake, and the basis of each
client attribution. Client identity is taken from the node's self-reported
gossip `clientId` plus its `version` string, and **re-read live at campaign
time** by the tool — if a target has switched client, the substitution rule in
`validators.json` applies and the change is recorded in the report. (Gossip
identity is self-reported; that is a stated limitation, cross-checked against
version strings and public validator registries at selection time.)

**The path of a transaction.** A Solana transaction has no mempool to sit in:
wallets and RPC nodes forward it (Gulf Stream) toward the current and upcoming
leaders over QUIC connections subject to stake-weighted quality of service.
The leader's TPU fetch stage receives it, SigVerify checks it, and the banking
stage — the component whose decisions this project measures — executes and
orders it into an entry; broadcast merely publishes the result. Our sender
submits through public RPC endpoints, which forward along this path; the
**path-control probe** (one per window, sent via a second independent RPC)
bounds how much of the observed order could be an artifact of the road rather
than the scheduler. We do **not** implement raw-QUIC TPU submission; that is a
stated non-separation (below).

**Interaction of our own transactions with each other.** Two transactions
conflict if one writes an account the other touches; conflicting transactions
must serialise, so a shared account would smuggle a second ordering force into
a fee experiment. The fee and arrival ladders therefore use pairwise
account-disjoint (payer, recipient) pairs drawn from the project's eight
funded accounts. The single deliberate exception is the **conflict pair**:
both members write the same account, with crossed fee/arrival order, to expose
the rule applied *inside* a conflict chain. All probes from one window target
the same block range, so cross-set contention for block space is part of the
measured reality and is why landed-in-window is the only credited outcome.

**Competition inside the block.** Our 11 probes compete with the block's real
traffic (hundreds of transactions). We never use absolute position as a
statistic — only the *relative* order of our own probes — so background load
shifts all our probes together and cannot manufacture a fee or arrival signal.

**Send order.** Fully recorded per probe (`send_seq`, intended price, local
timestamps in the send log). The fee ladder is sent cheapest-first, so the two
candidate rules make opposite predictions: fee-following inverts the send
order, arrival-following preserves it.

**Noise vs rule.** Each condition repeats across 3 windows per validator on
separate occasions. We pre-register the decision rule in `DESIGN.md`: a rule
is "observed" for a validator only when the rank correlation's direction is
consistent across windows; pooled client-level statistics use n=24 per ladder.
"No stable rule detectable at this probe scale" is an accepted, reportable
conclusion, per the brief.

**What this design does NOT separate.** (1) Scheduler behaviour vs. RPC
forwarding path — bounded by the path control, not eliminated; raw-QUIC TPU
submission would be needed for full separation. (2) The effect of block
fullness/load on the rule — recorded as context, not manipulated. (3) Jito
bundle interleaving — excluded by the brief (bundles and tips are a separate
mechanism); our Jito targets are measured on their ordinary transaction
stream only. (4) Fee *thresholds* finer than the four ladder rungs.

## Layout

```
probe/            the tool (RPC client, schedule, plan, gated sender, analyzer)
validators.json   target plan: 6 primaries + 3 alternates, with attributions
DESIGN.md         lean-budget campaign design + full fee arithmetic
config.example.json
data/             dry-run logs; send log, spend ledger, raw analysis (shipped as evidence)
reports/          REPORT.md (the final report), ANALYSIS_SUMMARY.md, READINESS.md;
                  REPORT_SKELETON.md / REPORT_TEMPLATE.md are the pre-campaign scaffolds
tests/            unit tests (python -m tests.test_units)
```

## Status

**Campaign complete — executed on Solana mainnet on 2026-10-31.** The
tool was verified to the funding gate on 2026-10-25 (14/14 unit tests,
mainnet dry-run — see `data/dry_run_*.log` — Docker build-context audit,
and a local-cluster live rehearsal; full record in
`reports/READINESS.md`). After the probe wallet
`CAtqKwVaYbZqB33sLNvsKNpr7Y8BnZf3X6V4PCjHrP2v` was funded from
free-bounty winnings (0.012 SOL), three live passes ran on 2026-10-31:
**462 probes broadcast, 42 landed in-window**, total ledger fees
2,986,220 lamports against the 10,000,000-lamport cap. Headline result:
in every window where in-window fee order was observable, landed order
preserved send order exactly (Spearman ρ = +1.0) and fee-following was
never observed at the four ladder price points; the arrival-ladder and
conflict-pair questions returned zero in-window observations and are
reported as not measured. The full dated report — methods, per-validator
and per-client statistics, limitations, and a complete "what went
wrong" section (burst lateness, blockhash expiry, skipped windows, and
every other deviation) — is **`reports/REPORT.md`**, with the
definitive statistics in `reports/ANALYSIS_SUMMARY.md` and all raw
signatures and slots in `data/`.
