# Readiness report — "Inside the Block" probe

Status as of **2026-10-25** (all verification performed 2026-10-25, UTC).
The tool is complete and verified up to the funding gate. **No mainnet
transaction has been sent.** The only remaining steps are funding the probe
wallet (from free-bounty winnings, per the operator's rule) and the live
run itself.

## What is complete

- **Targets**: 6 primary validators across 3 client implementations in
  `validators.json`, snapshotted from live RPC on 2026-10-25 and
  re-verified live at every check since (identities, clientId and version
  unchanged): JitoLabs — Kiln1, P2P.org; Firedancer 26.10.4 — Everstake,
  Galaxy; HarmonicAgave — Figment, Coinbase 04. Plus 3 alternates.
- **Probe implementation** (`probe/`): leader-schedule resolution with
  rotation-sized (≤4-slot) windows and a minimum planning lead
  (`min_window_lead_slots`, default 75 ≈ 30 s); burst sender that fetches
  one blockhash per RPC path, builds and signs all 11 probe transactions
  up front, then sends with the configured gaps; chronological execution
  across targets with passed windows skipped (never fired late); per-cycle
  idempotent sender top-ups; block-based landed-order recovery ordered by
  (slot, index-in-block); rank statistics with per-window breakdowns for
  the pre-registered cross-window sign-consistency rule.
- **Experiment sets** per window (11 txs): fee ladder (0 / 10k / 50k /
  250k µL-per-CU), arrival ladder (4 zero-fee, staggered), conflict pair
  (same sender + recipient + price, send order vs fee opposed), path
  control (same set via a second RPC endpoint). Every transaction is
  unique on the wire (transfer amount carries a 1–11 lamport dust nonce),
  so no two probes can collapse into one signature.
- **Safety rails, all in code**: dry-run by default (`send` without
  `--live` builds and signs with ephemeral keys and broadcasts nothing);
  live mode requires `--live`, a keypair file supplied via the
  `PROBE_KEYPAIR_FILE` environment variable, a set fee cap, and a minimum
  main-wallet balance; a spend ledger refuses any send that would push
  cumulative fees past the cap; keys are never read from the repository.

## Test evidence

`python3 -m tests.test_units` — **14/14 PASS** (2026-10-25):

- test_account_draw_within_float_per_cycle
- test_analyzer_orders_by_slot_then_index
- test_analyzer_per_window_breakdown
- test_base58
- test_ed25519_rfc8032_vector
- test_execute_window_burst_builds_with_one_blockhash_per_path
- test_fee_math
- test_keypair_roundtrip
- test_ledger_cap
- test_next_windows_cuts_long_runs_into_rotations
- test_next_windows_epoch_relative
- test_next_windows_never_returns_started_window
- test_stats
- test_window_plan_budget_and_disjointness

## Mainnet dry-run evidence (read-only / build-only)

- `probe schedule` (2026-10-25 ~01:49 UTC, current slot 461,076,594): all
  6 targets present in gossip with clientId/version identical to the
  snapshot; next 4-slot windows resolved for every target.
- `probe send` without `--live`: 11 signed transactions built for each of
  the 6 targets' next windows (66 total); nothing broadcast, no ledger
  written.
- `probe dry-run`: end-to-end log at **`data/dry_run_20261025T014902Z.log`**
  (schedule resolution + live client check + parsing of a real produced
  block with transaction-position extraction, 540 transactions).

## Docker evidence

- `docker compose config` parses the shipped compose file.
- The image build context was verified empirically in this sandbox
  (COPY-only build + filesystem export): the context contains the code,
  configs and docs, and **no keypair material** (`.dockerignore` excludes
  `*keypair*.json`, `.env`, `keys/`, `data/*.jsonl`, logs and bytecode
  caches; a COPY-layer grep for key material finds only the
  `probe/keypair.py` source module). `keys/` is mounted read-only at
  runtime and is gitignored.
- Full `docker compose build` + `docker compose run` could **not** be
  executed in this sandbox: its kernel lacks the iptables NAT module
  (bridge networking fails) and blocks the namespace operations runc
  needs (`setns: operation not permitted`). This is a property of the
  sandbox, not of the image: the Dockerfile's exact steps
  (`pip install -r requirements.txt`, then `python -m probe.cli
  dry-run`) were mirrored in a clean virtualenv on the host Python 3.12
  and completed successfully (log above). On any normal Docker host the
  one-command run is `docker compose run --rm probe`.

## Rehearsal evidence (no mainnet)

- **Devnet/testnet**: unreachable for funding from this network on
  2026-10-25 — devnet `requestAirdrop` returns 429 (faucet limit/dry) at
  2 / 1 / 0.1 SOL; testnet returns −32603 internal errors. The devnet
  pipeline itself (alternative validators/config files) was prepared and
  removed afterwards; the repo stays mainnet-focused.
- **Local cluster** (`solana-test-validator` v2.3.13; the v4.3.2
  validator panics in this sandbox because io_uring is blocked): the
  full live path ran end-to-end up to transaction landing — preconditions,
  planning, setup transfers (built, signed, accepted by RPC), and an
  11-probe burst. Two real bugs were found and fixed by this rehearsal
  (zero-lead planning; epoch-length windows for long leader runs).
  The probe whose payer existed executed its full instruction path in
  simulation (ComputeBudget + System program success, 450 CU). Landing
  itself could not be demonstrated: this sandbox's test-validator never
  executes **any** transaction — proven with the official Solana CLI as
  a control (its transfer was likewise accepted and never confirmed).
  Landing is a property of the cluster, not of the transactions, and the
  identical build/send path is exercised by the unit tests against a
  reference block parser.

## The exact live-run plan and its cost

- **Shape**: 6 validators × 3 windows × 11 probe transactions =
  **18 windows, 198 probe transactions**, windows per validator taken on
  separate occasions (`send --live --target <label> --windows 1` per
  occasion, or one `send --live --windows 3` run — the executor orders
  all windows chronologically and skips any that have passed).
- **Fees**: 55,570 lamports per window (fee ladder 40,000 base +
  15,200 priority; senders/arrival/conflict at base fee) → campaign
  probe fees **1,000,260 lamports**. Setup transfers add ≈35,000
  lamports per top-up occasion (7 × 5,000). **Code-enforced cap:
  10,000,000 lamports = 0.01 SOL** (`fee_cap_lamports` in `config.json`;
  absolute design ceiling 0.05 SOL is never approached).
- **Floats**: each of the 7 sender accounts is topped up to 200,000
  lamports over the rent-exempt minimum — 7 × 1,090,880 = **7,636,160
  lamports** leave the main account as floats and return via the
  end-of-campaign sweep (a documented manual step).
- **Net burn ≈ 1,070,260–1,245,260 lamports (≈0.0011–0.0013 SOL)** —
  probe fees + setup fees; everything else returns.
- **Funding instruction**: send **0.009 SOL** to the probe wallet's main
  account **`CAtqKwVaYbZqB33sLNvsKNpr7Y8BnZf3X6V4PCjHrP2v`** (the live
  precondition requires ≥ 9,000,000 lamports: floats + fees + headroom).
  Funding must come from free-bounty winnings, per the operator's rule;
  the funding deadline is ~2026-11-02/03 to leave ≥2 days for measuring
  and reporting before the submission deadline.

## Remaining steps after funding

1. Operator funds the probe wallet (above) and places the keypair file
   in `./keys/` (or any path outside the repo) for the run.
2. Live run: `PROBE_KEYPAIR_FILE=/keys/.probe_keypair.json docker compose
   run --rm probe send --live --windows 3` (or per-target occasions).
3. `probe analyze` → `data/analysis_*.json`; fill
   `reports/REPORT_TEMPLATE.md` (dated measurements; "what went wrong"
   section).
4. Before publishing the repo: force-add the raw data
   (`git add -f data/*.jsonl`) — the brief requires all signatures and
   slots for independent `getBlock` verification, and `.gitignore`
   excludes data files by default; the keypair file stays out (it is
   never committed; consider moving it outside the repo tree entirely).
5. **Submission is a human-account action**: the operator submits the
   public repo link + report on Superteam Earn from their own account
   before **2026-11-05T21:59:59Z** (the listing is HUMAN_ONLY; agent API
   submissions are rejected).

## Honest limits

- The two RPC paths are two endpoints into the same public
  infrastructure, not two network routes into the leader: the design
  bounds the RPC-vs-scheduler confound but cannot eliminate it without
  raw QUIC/TPU access, which is out of scope (and Jito bundles/tips are
  excluded by the brief anyway).
- Gossip `clientId` is self-reported by validators; mislabelled clients
  would blur the client-family comparison.
- The fee ladder resolves fee effects at 4 price points (0 / 10k / 50k /
  250k µL-per-CU); finer thresholds are not measurable with this design.
- 3 windows per validator is a rule-detection sample, not a
  characterization. A "no stable ordering rule / noise" result for some
  validators is an acceptable, reportable outcome — the pre-registered
  decision rules in `DESIGN.md` say exactly when that conclusion is
  reached.

## Live run outcome — 2026-10-31 (addendum)

The live campaign was executed once, exactly as planned above, after the
probe wallet was funded from free-bounty winnings. Facts only; all numbers
are from the tool's own logs/ledger, the analyzer output, and RPC
`getBalance` reads.

- **Pre-run balance**: 12,000,000 lamports at slot 463,494,420
  (precondition ≥ 9,000,000 met).
- **Invocation** (host route — Docker cannot run in this sandbox, see
  "Docker evidence"): `PROBE_KEYPAIR_FILE=<project dir>/.probe_keypair.json
  python3 -m probe.cli send --live --windows 3`, started
  2026-10-31T00:56:09Z, exit code 0, ~410 s; ledger activity
  00:56:20Z–01:02:59Z. Console log:
  `data/live_run_console_20261031T005609Z.log`.
- **Plan vs executed**: 18 windows planned (planned fees 1,000,260
  lamports, cap 10,000,000). **16 windows executed; 2 skipped** by the
  never-fire-late rule: `coinbase04_harmonic` window 463494856 and
  `galaxy_fd` window 463495000 (each had already started when its turn
  came, immediately after another target's burst).
- **Sent**: 176 probes (11/11 in every executed window), **0 send
  failures**; plus 32 setup funding transfers, all sent. Per validator —
  kiln1 33, p2p_org 33, everstake_fd 33, figment_harmonic 33,
  coinbase04_harmonic 22, galaxy_fd 22.
- **Fees (spend ledger)**: **1,049,120 lamports total** — probe fees
  889,120 (16 × 55,570, exactly the per-window design figure) + funding
  fees 160,000 (32 × 5,000). The cap was never approached.
- **Main account after**: **3,496,600 lamports** at slot 463,497,220.
  The −8,503,400 delta reconciles to the lamport: funding transfers out
  8,183,480 + funding fees 160,000 + main-paid probe fees 160,000 (the
  main account itself pays 2 of the 11 probes per window: fee-set rung 0
  and one arrival probe) + transfer dust out 96 − dust received as probe
  recipient 176. The floats remain in the 7 sender accounts; the
  end-of-campaign sweep (documented manual step) has **not** been
  performed.
- **Analysis**: `python3 -m probe.cli analyze` →
  `data/analysis_20261031T010526Z.json` (generated 2026-10-31T01:05:26Z).
  Of 176 probes: **10 landed in-window, 123 landed outside the window,
  43 never landed**. Outside-window landings were 1–8 slots after window
  end (median 5 slots ≈ 2 s). Per validator (in-window / outside /
  never): coinbase04_harmonic 0/14/8, everstake_fd 4/20/9,
  figment_harmonic 1/23/9, galaxy_fd 1/16/5, kiln1 2/27/4, p2p_org
  2/23/8. Only everstake_fd produced a fee-set ordering statistic
  (n=4, Spearman price-vs-position 1.0 — a very small sample); all other
  fee/arrival sets had n ≤ 2 in-window and no computable statistic, and
  no conflict pairs landed in-window. The bursts systematically landed
  a few slots after the target windows — with this run's public-RPC
  submission path, the probe bursts mostly missed the 4-slot leader
  windows they were aimed at.
- **Gossip at run time** (the tool's own `schedule` check,
  2026-10-31 ~00:55Z) differed from the 2026-10-25 snapshot for three
  targets: everstake_fd reported clientId=JitoLabs version=4.3.2
  (snapshot: Firedancer 26.10.4), galaxy_fd reported Firedancer 26.10.5
  (snapshot: 26.10.4), figment_harmonic reported HarmonicAgave 4.4.0
  (snapshot: 4.3.2). kiln1, p2p_org (JitoLabs 4.3.2) and
  coinbase04_harmonic (HarmonicAgave 4.3.2) matched the snapshot.
  (Gossip clientId is self-reported — see "Honest limits".)

## Burst-timing fix + live run 2 attempt — 2026-10-31 (addendum)

- **Code change** (`probe/sender.py`, `execute_window` only): the
  build-and-sign step was moved BEFORE the window wait. The sequence is
  now: fetch one blockhash per RPC path and build + sign all 11
  transactions → wait until `get_slot() >= window_start - 2` (trigger
  unchanged) → burst immediately. Run 1's order waited first and fetched
  blockhashes afterwards, and the two public-RPC round-trips of latency
  after the wait pushed the whole burst several slots late (10/176
  in-window; outside landings a median of 5 slots after window end).
  Building first is safe because a blockhash stays valid ~150 slots and
  planning guarantees ≥75 slots of lead (`min_window_lead_slots`).
  Nothing else changed: same transactions, order, gaps, sets, amounts
  and fees; no plan, analyzer or config changes.
- **Verification after the change**: unit suite **14/14 PASS**
  (`python3 -m tests.test_units`, including the one-blockhash-per-path
  burst test). A dry-run pass (`send` without `--live`) built 11
  transactions for each of the 6 targets (66 total), broadcast nothing,
  and left `spend_ledger.jsonl` and `send_log.jsonl` byte-identical
  (md5-verified before/after).
- **Gossip re-verification** before run 2
  (`data/schedule_check_20261031T011033Z.log`, 2026-10-31T01:10:33Z,
  slot 463,498,667): identical picture to run 1 — everstake_fd reported
  JitoLabs 4.3.2 (snapshot: Firedancer 26.10.4), galaxy_fd Firedancer
  26.10.5 (snapshot: 26.10.4), figment_harmonic HarmonicAgave 4.4.0
  (snapshot: 4.3.2); kiln1, p2p_org (JitoLabs 4.3.2) and
  coinbase04_harmonic (HarmonicAgave 4.3.2) matched the snapshot.
- **Run 2 did NOT execute — refused by the tool's own funding gate.**
  Pre-run main balance re-verified at **3,496,600 lamports** (slot
  463,498,703). The exact run-1 invocation
  (`PROBE_KEYPAIR_FILE=<project dir>/.probe_keypair.json python3 -m
  probe.cli send --live --windows 3`) was started 2026-10-31T01:10:47Z
  and exited with code 2: `REFUSED: main wallet balance 3496600
  lamports < required minimum 9000000` (console log:
  `data/live_run2_console_20261031T011047Z.log`). The live precondition
  (`min_wallet_balance_lamports` = 9,000,000 in `config.json`) was
  written for a freshly funded campaign and does not credit the
  7,636,160 lamports of sender floats run 1 left in the 7 sender
  accounts, so the main account sits below the gate even though a
  second pass's floats are already in place and one pass needs only
  ~1.0–1.05M lamports of fees plus minor top-ups.
- **Effect of the attempt: none.** Zero transactions sent, zero fees
  spent; `spend_ledger.jsonl` and `send_log.jsonl` byte-identical
  after the attempt (md5-verified); main balance unchanged at
  3,496,600 lamports (slot 463,498,827); cumulative ledger fees remain
  1,049,120 lamports and the dataset remains run 1 only (the analyzer
  was not re-run — it would reproduce the run-1 output). The
  burst-timing fix is in place and unit-verified but has **no live
  measurement yet**. Unblocking run 2 requires an operator decision
  outside this fix's scope: lower the config minimum for a
  floats-already-funded pass, or sweep the floats back to the main
  account first, or top the main account up by ≥5,503,400 lamports.

## Funding-gate adjustment for run 2 — 2026-10-31 (addendum, operator decision)

- **Config change** (`config.json`, one value only):
  `min_wallet_balance_lamports` lowered from **9,000,000 to 2,000,000**.
  Nothing else in the config was touched. The 9,000,000 figure was
  derived for a *fresh* campaign: it had to cover deploying
  **7,636,160 lamports** of sender floats (7 accounts topped up to
  1,090,880 lamports each) plus the main account's own probe and
  transfer fees plus headroom. For this second pass the floats are
  already deployed — run 1 left them in the 7 sender accounts (the
  senders paid ~729,120 lamports of run-1 probe fees out of those
  floats), so the gate as written double-counts capital that is
  already in place.
- **Float-aware justification**: the true marginal cost of a second
  pass is ≤ ~1.2M lamports — sender top-up shortfalls after run 1
  (≈ ≤800K), the main account's own probe fees (~160K), and
  funding-transfer fees (≤ ~175K). The main account holds
  **3,496,600 lamports** (≈ 3× the marginal need), and the lowered
  2,000,000 gate still sits above the marginal-need estimate, so the
  precondition remains a real check rather than a formality.
- **Spend cap unchanged**: the cumulative fee cap
  (`fee_cap_lamports` = **10,000,000 lamports**, enforced by the spend
  ledger) was NOT altered. Cumulative fees before run 2 stand at
  **1,049,120 lamports** (run 1).
- **Verification after the change**: unit suite **14/14 PASS**
  (`python3 -m tests.test_units`).
- This adjustment is an **operator decision for a second pass** on an
  already-float-funded campaign, recorded here in full so the final
  report can cite it transparently; it is not a change to the tool's
  safety model — the ledger cap, the per-window plan/budget checks
  and the dry-run default are all untouched.

## Live run 2 outcome — 2026-10-31 (addendum)

- **Execution**: after the gate adjustment above, the main balance was
  re-verified by RPC at **3,496,600 lamports** (slot 463,499,359) and
  the campaign ran 2026-10-31T01:13:07Z–01:25:19Z with the standard
  invocation (`send --live --windows 3`); console log:
  `data/live_run2_console_20261031T011307Z.log`. Of the **18 planned
  windows**: **12 executed fully (11/11 sent)**, **4 sent 0/11**, and
  **2 were skipped** (window already started or passed:
  p2p_org 463500084, coinbase04_harmonic 463501396). Probes:
  198 planned → 176 attempted → **132 broadcast**.
- **Anomaly — the four 0/11 windows** (p2p_org 463500264 and
  463500740, kiln1 463501236, coinbase04_harmonic 463502600): all 44
  probes failed at simulation with `BlockhashNotFound` (RPC code
  -32002) after 4 send tries and were **never broadcast** (no fees
  charged for them). With the burst-timing fix, transactions are built
  and signed before the window wait; for these windows the blockhash
  fetched up front had aged past its ~150-slot validity by send time.
  This is the fix's known trade-off surfacing on later-queued windows;
  it is recorded here as measured fact, not adjusted away.
- **Landing results — run 2 alone** (132 sent): **in-window 22
  (16.7%)**, outside-window 86, never landed 24. Per validator
  (sent / in / out / never): galaxy_fd 33/10/23/0;
  figment_harmonic 33/5/23/5; everstake_fd 33/3/11/19;
  kiln1 22/3/19/0; coinbase04_harmonic 11/1/10/0; p2p_org 0/0/0/0
  (all three of its windows were skipped or blockhash-failed).
- **Landing results — combined dataset** (run 1 + run 2 pooled, as
  DESIGN.md intends; analyzer output
  `data/analysis_20261031T012938Z.json`): **308 sent → in-window 32
  (10.4%), outside-window 209, never landed 67**. Per validator
  (sent / in / out / never): everstake_fd 66/7/31/28;
  figment_harmonic 66/6/46/14; galaxy_fd 55/11/39/5;
  kiln1 55/5/46/4; coinbase04_harmonic 33/1/24/8; p2p_org 33/2/23/8.
  For reference, run 1 alone was 10/176 in-window (5.7%): the
  burst-timing fix roughly tripled the in-window share in run 2
  (16.7%), but outside-window landings still dominate the dataset.
- **Fees**: the spend ledger accounts **1,014,120 lamports** for
  run 2 (this is the ledger's conservative accounting — it includes
  the planned fees of the 44 never-broadcast probes, which were not
  actually charged on-chain). **Cumulative ledger total:
  2,063,240 lamports** against the unchanged 10,000,000 cap.
  Main-account balance after run 2: **2,617,611 lamports**
  (RPC-verified, slot 463,503,495; pre-run 3,496,600 — the
  878,989-lamport main-side delta covers the run's funding transfers
  plus main-paid fees; landed sender probes were additionally paid
  out of the deployed sender floats). Sender floats were NOT swept.

## Blockhash freshness fix + live run 3 (final pass) — 2026-10-31 (addendum)

- **Code change** (`probe/sender.py`, `execute_window` only; new module
  constant `BLOCKHASH_MAX_AGE_SLOTS = 100`): at build time the executor
  now records, per RPC path, the chain slot at which that path's
  blockhash was fetched (one extra `get_slot` read per path — build time
  is not latency-critical). At burst time, immediately before the first
  send, any path whose blockhash has aged past 100 slots (a safety
  margin under the ~150-slot blockhash validity) is re-fetched ONCE and
  that path's transactions are re-signed with it via the existing build
  function (local CPU work). Paths still fresh fire exactly as built.
  Nothing else changed: transactions, sets, order, gaps, amounts, fees,
  wait trigger, plan, analyzer and config are untouched. This targets
  run 2's measured failure: 44 probes in four later-queued windows
  reached the burst with an upfront blockhash older than its validity
  and failed simulation with `BlockhashNotFound` (RPC −32002), never
  broadcast.
- **Verification before the live run**: unit suite **14/14 PASS**
  (`python3 -m tests.test_units`, including the
  one-blockhash-per-path burst test — in the fresh case the freshness
  check performs no re-fetch). A scripted fresh/stale functional check
  (fake RPCs, deterministic keypairs) confirmed the stale branch: the
  aged path made exactly one extra blockhash fetch and its probes were
  re-signed with the fresh blockhash, while the still-fresh path's
  probe was byte-identical to the fresh-scenario build. A dry-run pass
  (`send` without `--live`) built 11 transactions for each of the 6
  targets (66 total), broadcast nothing, and left
  `spend_ledger.jsonl` and `send_log.jsonl` byte-identical
  (md5-verified before/after); console saved as
  `data/dry_send_check_20261031T013435Z.log`.
- **Pre-run checks**: main balance re-verified by RPC at **2,617,611
  lamports** (slot 463,505,395 — exactly the post-run-2 figure; config
  gate of 2,000,000 met). Fresh gossip/schedule check
  (`data/schedule_check_20261031T013442Z.log`, slot 463,505,425)
  showed the same run-time picture as runs 1–2: everstake_fd on
  JitoLabs 4.3.2 (not its Firedancer snapshot), galaxy_fd Firedancer
  26.10.5, figment_harmonic HarmonicAgave 4.4.0, kiln1 and p2p_org
  JitoLabs 4.3.2, coinbase04_harmonic HarmonicAgave 4.3.2.
- **Execution**: `PROBE_KEYPAIR_FILE=<project dir>/.probe_keypair.json
  python3 -m probe.cli send --live --windows 3`, started
  2026-10-31T01:34:57Z, exit code 0; console log:
  `data/live_run3_console_20261031T013457Z.log`. Of the **18 planned
  windows**: **14 executed fully (11/11 sent)** and **4 skipped** by the
  never-fire-late rule (kiln1 463505952, p2p_org 463505968,
  kiln1 463506052, galaxy_fd 463506104 — each immediately behind another
  target's burst). Probes: **154 attempted → 154 broadcast, 0 send
  errors — no BlockhashNotFound losses recurred**, including the
  late-queued windows (p2p_org 463506560, everstake_fd 463506292 and
  463506672, coinbase04_harmonic 463506092) whose sparse spacing is the
  run-2 failure shape.
- **Landing results — run 3 alone** (154 sent): **in-window 10 (6.5%)**,
  outside-window 99, never landed 45. Per validator (sent / in / out /
  never): coinbase04_harmonic 33/3/19/11; everstake_fd 33/5/27/1;
  figment_harmonic 33/2/24/7; galaxy_fd 22/0/17/5; kiln1 11/0/2/9;
  p2p_org 22/0/10/12. Run 3 removed run 2's send-layer losses entirely
  but its in-window share fell back toward run 1's level: the bursts
  still mostly reach leaders at or after the 4-slot windows close
  (outside landings 1–8 slots after window end, median 5).
- **Combined dataset (runs 1+2+3)**: 462 sent → **in-window 42 (9.1%),
  outside-window 308, never landed 112**. Analyzer output:
  `data/analysis_20261031T014525Z.json`; the definitive combined
  analysis (per-run and per-validator counts, fee/arrival/conflict
  statistics per validator and per run-time client, landed-slot offset
  quantification, fees) is in **`reports/ANALYSIS_SUMMARY.md`**. All 42
  in-window landings are fee-set probes; where computable, fee-set
  landed order matched send order exactly (Spearman ρ = +1.0,
  sign-consistent across all 12 windows with a per-window statistic,
  per-window n = 2–4) — no fee-following observed in-window; arrival
  and conflict statistics are not computable (zero in-window
  observations for both sets).
- **Fees**: spend ledger accounts **922,980 lamports** for run 3
  (probe 777,980 = 14 windows × 55,570 exactly, plus funding 145,000 =
  29 transfers × 5,000). **Cumulative ledger total: 2,986,220
  lamports** against the unchanged 10,000,000 cap. Main-account
  balance after run 3: **1,876,581 lamports** (RPC-verified, slot
  463,506,723); the −741,030 delta from 2,617,611 reconciles to the
  lamport (funding transfers out 456,100 + funding fees 145,000 +
  main-paid probe fees 140,000 + probe dust sent 84 − dust received
  154). Sender floats were NOT swept.
- **This was the final data-collection pass.** No run 4 follows,
  whatever the yield; remaining steps are the report fill, the public
  repo, and the operator's own submission (see "Remaining steps after
  funding" — the sweep stays a documented manual operator action).

## Teardown attempt — HALTED, no sweep command exists — 2026-10-31 (addendum)

- A teardown pass was started on 2026-10-31 (~01:59Z) to sweep the
  sender floats back to main and return the remainder to the operator's
  personal Solana wallet. It was **halted before any transfer** on a
  tooling fact found during pre-flight:
  - The CLI exposes only `keygen, schedule, plan, dry-run, send,
    analyze` — **there is no sweep command**.
  - `probe/sender.py`'s docstring states the sweep "is an operator
    action at campaign end (documented in the README), not automated
    here" — but `README.md` contains **no mention of a sweep at all**;
    no documented, runnable sweep procedure exists anywhere in the
    project. Every READINESS reference to a "documented manual step"
    points at documentation that was never written.
  - Per the teardown's own guardrail (no hand-rolled transfers out of
    the sender accounts), **zero transfers were made**: no sweep, and
    consequently no return transfer to the operator's wallet either.
    Resolving this needs an operator decision to implement a sweep
    (e.g. a small teardown script using the project's own modules).
- **Exact on-chain state at halt** (RPC `getBalance`, slot 463,512,223):
  main `CAtqKwVaYbZqB33sLNvsKNpr7Y8BnZf3X6V4PCjHrP2v` = **1,876,581**
  (unchanged from post-run-3); S1 = 1,091,930; S2 = 1,000,718;
  S3 = 1,059,368; S4 = 1,030,520; S5 = 1,091,300; S6 = 1,029,308;
  S7 = 1,060,826 — sender floats total **7,363,970**; project total
  **9,240,551 lamports**. The operator's personal wallet
  `EMCzkUmfVLcbey2eugzppupQkz4Z8FiosLpMP9opUDv1` read **3,071,497**
  lamports, unchanged. Nothing about the campaign data or the report
  depends on this state; the funds simply remain where run 3 left them
  until a sweep is implemented.

## Teardown — COMPLETED, sweep + return executed — 2026-10-31 (addendum)

- The operator authorized implementing the missing sweep as a small
  script on the project's own modules. `teardown.py` (project root)
  uses only `probe/keypair.py`, `probe/txbuild.py` and `probe/rpc.py`
  (keys loaded via `PROBE_KEYPAIR_FILE`, never printed), building
  plain price-0 transfers exactly like `sender.setup_accounts`' funding
  transfers (one signature, 5,000-lamport base fee each). Two phases
  with per-transfer on-chain reconciliation; any mismatch would have
  halted the run with no further transfers. None occurred.
- **Pre-flight** (read-only snapshot, slot 463,512,833) matched the
  halted state above to the lamport: main 1,876,581; S1..S7 =
  1,091,930 / 1,000,718 / 1,059,368 / 1,030,520 / 1,091,300 /
  1,029,308 / 1,060,826 (floats 7,363,970; project total 9,240,551);
  operator wallet 3,071,497. Full run: 2026-10-31T02:01:18Z–02:01:48Z,
  slots 463,512,855 → 463,512,995; console log
  `data/teardown_console_20261031T0201Z.log`.
- **Phase A — sweep S1..S7 → main** (each sender read live, swept
  balance − 5,000 fee, then verified at exactly 0 with main increased
  by exactly the swept amount):
  - S1: 1,091,930 → **1,086,930**, sig
    `p4BiW1xmM2R5cLfQqF1389Uxnn7e6fhq7enELhDvhDJLK1NtyhdtLj1TmrJiAfcBH4XKvY56MEEnuzqxAmt5EU7`; main after 2,963,511
  - S2: 1,000,718 → **995,718**, sig
    `3HujEUFfehUkCdCWYJigKaLNScJfzknNnbBMVUA9xurnbP6dmrz5zYsgFMKF96iikkoWojLXqW3p75GCs8BYvWe`; main after 3,959,229
  - S3: 1,059,368 → **1,054,368**, sig
    `2nd7JzmpSgQWanGEsEdLNM2j15LrhbGrpqFAdruSiKMCouBTULRiedviqwdj4JDseEmfFWEvvYCEuXqjY4bQr4zP`; main after 5,013,597
  - S4: 1,030,520 → **1,025,520**, sig
    `496nyfUgRC9tvhgDuUFt4T4E6qoWMDVQHbpz8b7tQXeQ7tNHc28c3ZvdxdT7dDuj1iboo99bX8DgWpbkvHNVKBBm`; main after 6,039,117
  - S5: 1,091,300 → **1,086,300**, sig
    `2c9L3dH1aGoJs2tvYo4ToNFZ4wwAXncaEPsoWyGZFTq1T5P9xDnwEQeeExih5JrvCGwxx5cNRUaKmsfuCz6H3V4z`; main after 7,125,417
  - S6: 1,029,308 → **1,024,308**, sig
    `F9LnGDne6qdKnJbZzdV6MUxJH3eNUx3MdwWkqeYXkr67pdMHj8VixxCbnxaNVCU4QmD5vA3NKwtCuL8aN6uWJXq`; main after 8,149,725
  - S7: 1,060,826 → **1,055,826**, sig
    `cBZUAChzKzPYBoRDEP7qHDbiBVvvwHN83V8t8KK6yqYHh1kFWEEhY1yK8vkyK3sYqw4sEfzrYF9pj6Fn3Un8P1k`; main after 9,205,551
  - **Total recovered: 7,328,970 lamports** (floats 7,363,970 − 7 ×
    5,000 fees); main after Phase A = **9,205,551** (1,876,581 +
    7,328,970).
- **Phase B — return main → operator wallet**
  `EMCzkUmfVLcbey2eugzppupQkz4Z8FiosLpMP9opUDv1`: main read live at
  9,205,551; returned **8,309,671 lamports** (= 9,205,551 − 890,880
  rent-exempt reserve − 5,000 fee), sig
  `4TPba6A62RjiTc5ms4RkSuwBruytTdoPhgsdDFmK4tMhrbxxX14ocQepfr1mcTQ3R6zDEyAcE3Q3NksVKma4T4fR`.
  Verified to the lamport: main after = **890,880** (exactly the
  rent-exempt minimum, left in place); operator wallet 3,071,497 →
  **11,381,168** (delta exactly 8,309,671).
- **Final on-chain state** (RPC `getBalance`, slot 463,512,995):
  main `CAtqKwVaYbZqB33sLNvsKNpr7Y8BnZf3X6V4PCjHrP2v` = **890,880**;
  S1..S7 = **0** each; operator wallet = **11,381,168**. The campaign
  is now fully torn down: every recoverable lamport is back with the
  operator, and the only lamports left in the project are main's
  rent-exempt reserve.
