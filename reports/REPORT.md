# Inside the Block: How Solana Validators Order Transactions

**Bounty:** Superteam Earn — "Inside the Block: How Solana Validators
Order Transactions", sponsored by Superteam Ukraine, published
2026-10-22.
**Listing:** https://earn.superteam.fun/listing/inside-the-block-how-solana-validators-order-transactions/
**Network:** Solana Mainnet only.
**Alpenglow side:** after — the upgrade activated on mainnet on
2026-10-21; every measurement in this report was taken after it, and no
pre-upgrade data exists in this project or is pooled with these results.
**Campaign dates:** 2026-10-31 (UTC). All live sends fall between
2026-10-31T00:56:20Z (first send-log entry) and 2026-10-31T01:39:11Z
(last send-log entry), in three live passes started at 00:56:09Z,
01:13:07Z and 01:34:57Z. Target windows span slots 463,494,708 –
463,506,672; landed probes were recovered from slots 463,494,714 –
463,506,683. The canonical analysis (`data/analysis_20261031T014525Z.json`)
was generated 2026-10-31T01:45:25Z.
**Probe wallet (public):** `CAtqKwVaYbZqB33sLNvsKNpr7Y8BnZf3X6V4PCjHrP2v`
**Total fees spent:** 2,986,220 lamports (0.00298622 SOL) per the spend
ledger (`data/spend_ledger.jsonl`), of the 10,000,000-lamport (0.01 SOL)
code-enforced cap. The ledger figure is a **conservative upper bound**
on on-chain fees: it books the planned fees of 44 run-2 probes that
were never broadcast and never charged (§9.2, item k).
**Raw data:** `data/send_log.jsonl`, `data/spend_ledger.jsonl`,
`data/analysis_*.json` — signature and slot for every probe sent; any judge
can verify every claim below with `getBlock`.

**How this report maps to the judging criteria.** *Design (35%)* — §2–§4:
a pre-registered experiment whose two candidate rules make opposite,
falsifiable predictions. *Verifiability & reproducibility (25%)* — §5:
one-command reproduction and complete raw data. *Analysis (25%)* — §6–§8:
pre-registered interpretation rules, honest limitations, null results
reported as conclusions. *Engineering (15%)* — §4.5 and §9: dry-run by
default, a code-enforced spend cap, full logging, containerisation, and a
dated record of everything that went wrong.

---

## 1. Research question and pre-registered hypotheses

**Question (per validator).** When this validator leads, what rule decides
which of our transactions lands earlier — fee-per-compute-unit, arrival
order, or no stable rule at probe scale — and how strictly does that rule
hold inside conflict chains, where transactions that write the same account
must serialise?

This question matters because the order of a block is decided privately,
inside one machine, by the leader's scheduler. Solana has no public
mempool: a transaction is forwarded directly toward upcoming leaders (Gulf
Stream) and processed within roughly 400 ms, so by the time a block is
public the ordering question has already been answered. The reference
client's documented rule (Agave's central scheduler with its priority
graph) is: among received and verified transactions, schedule by fee
density — the priority fee expressed as a price in micro-lamports per
compute unit — respecting account conflicts, until the block's budgets are
full. Whether production validators, running three different client
implementations, actually behave that way under load is not documented
anywhere. It can only be measured, with transactions we send ourselves,
whose contents, fees, send order and send times we control and record.
Other transactions in the same blocks are context, never evidence.

**Pre-registered hypotheses.** For each target validator, exactly one of
the following is concluded, by the decision rules fixed in `DESIGN.md`
before any live send:

- **H1 — fee-density following.** The fee ladder's landed order follows
  price: Spearman's ρ between price and landed position
  (`fee_set.spearman_price_vs_position` in the analysis output) is
  negative and its sign is consistent across the validator's 3 windows
  (§7 gives the exact conventions and the consistency bar).
- **H2 — arrival following.** The arrival ladder's landed order preserves
  send order: Spearman's ρ between send order and landed position
  (`arrival_set.spearman_sendorder_vs_position`) is positive and
  sign-consistent across windows, while the fee ladder shows no consistent
  fee effect.
- **H0 — no stable rule detectable at this probe scale.** Neither
  correlation is sign-consistent across windows. **This is a legitimate,
  pre-registered outcome, not a failed experiment** — the listing's
  analysis criteria state it explicitly, and `DESIGN.md` fixes in advance
  exactly when this conclusion is reached. A null result with tight
  methodology outranks a confident story.

**Conflict-chain sub-question.** Within the crossed conflict pair (zero-fee
sent first, 250,000 µL/CU sent second, both writing the same account), does
the higher-fee transaction reliably take the earlier serial position? Per
client family the outcome is reported as fee-wins out of 6 pairs with its
binomial weight (6/6 ⇒ p ≈ 0.016 under a fair-coin null; 5/6 ⇒ p ≈ 0.11,
reported as suggestive only). As executed, this sub-question could not be
scored at all: **0 of the 42 attempted pairs had both members land
in-window** (§6, §9.2 item e), so no fee-win count exists for any family.

## 2. Targets

Six production validators, two per client family, spanning three distinct
client implementations — the listing's minimum, chosen from live cluster
data. Targets were snapshotted from live mainnet RPC on 2026-10-25
(`validators.json`: vote/identity pubkeys, stake, attribution basis) and
re-verified live in gossip at every check since; the tool re-reads each
target's `clientId` and `version` from gossip at campaign time, and the
client column in the results table (§6) is that live value, not the
snapshot. If a target has switched client or gone delinquent by campaign
time, the substitution rule in `validators.json` applies (three verified
alternates are recorded there) and the change is recorded in §9.

| Label | Operator | Client family | Client (snapshot) | Version (snapshot) | Activated stake at snapshot (SOL) |
|---|---|---|---|---|---|
| kiln1 | Kiln1 | Jito-Solana (Agave fork) | JitoLabs | 4.3.2 | 5,973,285 |
| p2p_org | P2P.org | Jito-Solana (Agave fork) | JitoLabs | 4.3.2 | 4,860,667 |
| everstake_fd | Everstake | Firedancer (independent C client) | Firedancer | 26.10.4 | 7,785,036 |
| galaxy_fd | Galaxy | Firedancer (independent C client) | Firedancer | 26.10.4 | 7,038,249 |
| figment_harmonic | Figment | Harmonic (Agave fork) | HarmonicAgave | 4.3.2 | 17,099,113 |
| coinbase04_harmonic | Coinbase 04 | Harmonic (Agave fork) | HarmonicAgave | 4.3.2 | 3,649,998 |

Client attribution is the node's self-reported gossip `clientId`
cross-checked against its `version` string, corroborated for Firedancer by
the 26.10.x release line (docs.firedancer.io) and for operator names by
public validator registries — stated as a limitation in §8, since gossip
identity is self-reported. At snapshot time (2026-10-25) the three families
covered ≈ 22.96% (JitoLabs), ≈ 7.01% (Firedancer) and ≈ 21.56%
(HarmonicAgave) of activated stake across 665 current validators
(`validators.json`, live RPC). There is no Frankendancer target:
Frankendancer is not supported under Alpenglow and no longer exists on
mainnet, so the post-upgrade third family is the full Firedancer client.

**Run-time attribution (what §6 uses).** Gossip re-reads at all three
run-time checks on 2026-10-31 (before run 1, ~00:55Z; before run 2,
01:10:33Z; before run 3, 01:34:42Z) agreed with each other but differed
from the 2026-10-25 snapshot for three targets:

| Label | Snapshot (2026-10-25) | Run-time (all three checks, 2026-10-31) |
|---|---|---|
| kiln1 | JitoLabs 4.3.2 | JitoLabs 4.3.2 |
| p2p_org | JitoLabs 4.3.2 | JitoLabs 4.3.2 |
| everstake_fd | Firedancer 26.10.4 | **JitoLabs 4.3.2** |
| galaxy_fd | Firedancer 26.10.4 | **Firedancer 26.10.5** |
| figment_harmonic | HarmonicAgave 4.3.2 | **HarmonicAgave 4.4.0** |
| coinbase04_harmonic | HarmonicAgave 4.3.2 | HarmonicAgave 4.3.2 |

No alternate substitution was made: the targets' identities and operator
were unchanged, and the pre-registered design measures validators, with
client attribution taken live (this is the substitution rule's "record the
change" branch, recorded here and in §9.2). The consequences for pooling
are material and are carried through §6.2: the run-time **JitoLabs** pool
is kiln1 + p2p_org + everstake_fd, **Firedancer** rests on galaxy_fd
alone, and **HarmonicAgave** is figment_harmonic + coinbase04_harmonic.
No conclusion in this report attributes everstake_fd's measurements to
Firedancer.

**Dry-run target evidence (2026-10-25, read-only).** `probe schedule` at
slot 461,076,594 (≈ 01:49 UTC) found all 6 targets present in gossip with
clientId/version identical to the snapshot and resolved each target's next
4-slot leader windows; `probe dry-run` additionally parsed a real produced
block (540 transactions) and demonstrated transaction-position extraction
(full log: `data/dry_run_20261025T014902Z.log`).

## 3. Design and method

### 3.1 Windows

The leader schedule is published an epoch ahead and leaders serve runs of
consecutive slots (normally 4). A **window** is one target's leader run,
cut to rotation size (≤ 4 slots) and aligned to the run start; a window is
used only whole — never as the tail of a run that has already started.
Planning enforces a minimum lead, `min_window_lead_slots` in `config.json`
(default 75 slots ≈ 30 s), so probes are built and signed well before they
must arrive. Windows that have passed by execution time are skipped, never
fired late. Each validator was to be measured in **3 windows on separate
occasions** (different leader rotations, spread across the campaign), so a
single machine state cannot masquerade as a rule.

**As executed** — disclosed here and in §9.2/§11: the campaign ran as
three full passes on a single morning (2026-10-31, ≈ 00:56Z, ≈ 01:13Z,
≈ 01:35Z). Each pass planned 3 fresh windows per validator in distinct
leader rotations, so across the three passes the validators accumulated
5–9 executed windows each (42 executed windows in total). The
"separate occasions / distinct leader rotations" property holds; the
"spread across campaign days" intent of `DESIGN.md` does not, and the
results are read with that limitation.

### 3.2 The probe set — 11 transactions per window

All probes are dust transfers between the project's own 8 accounts (main +
S1..S7). Every transaction is unique on the wire: the transfer amount
carries a 1–11 lamport dust nonce encoding the send sequence, so no two
probes under one blockhash can collapse into one signature (§9.1 records
the collision hazard this removes). Each sender is topped up per cycle to
the rent-exempt minimum (890,880 lamports) plus a 200,000-lamport float;
the top-up is idempotent and sized so no account can run dry inside a
cycle (the heaviest payer draws 45,030 lamports per 3-window cycle).

| Set | n | Construction (accounts, price, send pattern) | What it isolates |
|---|---|---|---|
| Fee ladder | 4 | Pairs (M→S1), (S2→S3), (S4→S5), (S6→S7) — pairwise account-disjoint. Compute-unit prices 0 / 10,000 / 50,000 / 250,000 µL-per-CU, **sent cheapest first** (0.08 s gaps). | The fee-density rule. The two candidate rules make opposite predictions: fee-following inverts the send order; arrival-following preserves it. |
| Arrival ladder | 4 | The same 4 disjoint pairs, all at price 0, rapid burst (0.03 s gaps), send order recorded per probe (`send_seq`). | Whether arrival order survives at all, and its jitter. |
| Conflict pair | 2 | (S2→S1) at price 0 sent first; (S3→S1) at 250,000 µL/CU sent second (0.05 s gap). Both write S1 ⇒ must serialise. | The rule *inside* a conflict chain — the case users actually feel on contested accounts. |
| Path control | 1 | (S7→M) at 10,000 µL/CU, sent via the alternate public RPC endpoint (`rpc_url_alt`). | Scheduler rule vs. the road to the scheduler (RPC forwarding path). |

The fee and arrival ladders use pairwise account-disjoint (payer,
recipient) pairs deliberately: two transactions conflict if one writes an
account the other touches, and a shared account would smuggle a second
ordering force into a fee experiment. The conflict pair is the single
deliberate exception. Ladder transactions carry a fixed compute-unit limit
of 1,000 (a transfer plus two Compute Budget instructions needs ~300; the
limit sets the priority-fee basis, so it is kept small and fixed), making
the actual priority fees 0 / 10 / 50 / 250 lamports on top of the
5,000-lamport base fee per signature.

Probes are fired to arrive inside the window, via public RPC endpoints
(main: `https://api.mainnet-beta.solana.com`; the path control uses
`https://solana-rpc.publicnode.com`), which forward toward the leader
along the Gulf Stream path. All probes from one window target the same
block range, so cross-set contention for block space is part of the
measured reality — which is why **landed-in-window is the only credited
outcome**: the read-back credits a probe to a target only if it landed
inside that window's slots; a probe landing in the next leader's block is
recorded as landed-outside-window (a miss), never as evidence about the
target, and a probe that never lands is recorded as such — a rule about
ordering that ignored systematic drops would be a fairy tale.

**A collinearity caveat (from `DESIGN.md`, and decisive for reading §6).**
The fee ladder is sent cheapest-first, so within the fee set the price
order and the send order are identical by construction: ρ(price) and
ρ(send-order) on the fee set are necessarily equal. The two candidate
rules are discriminated by the *sign* of that single statistic —
fee-following would appear as a strongly **negative** ρ (landed order
reversed against both orders), arrival-preservation as a **positive** ρ.
The independent test of arrival order is the arrival ladder, whose
send order is the only ordering force in play.

### 3.3 Campaign shape and spend

The design fixes 6 validators × 3 windows × 11 probes = **18 windows,
198 probe transactions** per pass. Fees per window are fully determined
by the construction: fee ladder 20,310 + arrival ladder 20,000 +
conflict pair 10,250 + path control 5,010 = **55,570 lamports per
window**, hence 1,000,260 lamports of probe fees for a full 18-window
pass. Setup transfers add ≈ 35,000 lamports per top-up occasion
(7 × 5,000). The **code-enforced spend cap is 10,000,000 lamports
(0.01 SOL)** — `fee_cap_lamports` in `config.json`, 5× below the
listing's ≈ 0.05 SOL ceiling, which is a ceiling and not a target: the
cap is cumulative, the spend ledger counts every attempted send (failed
transactions still pay fees), and there is no override. Expected **net
burn ≈ 1,070,260–1,245,260 lamports (≈ 0.0011–0.0013 SOL)** — probe fees
plus setup fees; the sender floats (7 × 1,090,880 = 7,636,160 lamports)
leave the main account only as float and return via the end-of-campaign
sweep.

As executed, three passes were run (a second and third pass were made to
recover in-window yield after the timing failures documented in §9.2):
**462 probes were broadcast in total** (176 + 132 + 154), plus 44 further
probes attempted in run 2 but never broadcast (§9.2 item b). Total fees
actually spent, per the spend ledger: **2,986,220 lamports
(0.00298622 SOL)** — run 1: 1,049,120 (probe 889,120 + funding 160,000);
run 2: 1,014,120 (probe 889,120 + funding 125,000); run 3: 922,980
(probe 777,980 + funding 145,000). As noted in the header, the ledger
total is a conservative upper bound on on-chain fees (§9.2 item k). The
10,000,000-lamport cap was never approached: cumulative ledger fees
reached 29.9% of the cap. Main-account balance: 12,000,000 lamports
before run 1 → 3,496,600 after run 1 → 2,617,611 after run 2 →
**1,876,581 after run 3** (slot 463,506,723); the run-3 delta reconciles
to the lamport (§9.2). Sender floats remain deployed in the 7 sender
accounts; the end-of-campaign sweep has **not** been performed (it is a
manual operator step and moves no measurement data).

### 3.4 Ground-truth recovery

After each window, the produced blocks are fetched and every probe
signature is located: the analyzer records, per probe, its **slot** and
its **index within the block** (`records[].slot`, `records[].index`,
plus `records[].block_tx_count`) — landed order is ordered by
**(slot, index-in-block)**. Statistics never use absolute position: only
the **relative order of our own probes within the window** (window-relative
ranks), so background traffic — hundreds of transactions per block —
shifts all our probes together and cannot manufacture a fee or arrival
signal, and window ranks pool across windows without comparing raw indices
across blocks. "Never landed" means: not found in the searched span —
the window plus the 8 following slots.

### 3.5 Safety design (engineering)

- **Dry-run by default.** `send` without `--live` builds and signs all 11
  probe transactions per target with ephemeral keys and broadcasts
  nothing; the shipped one-command demo (`docker compose run --rm probe
  dry-run`) needs no keys at all.
- **Live mode is gated four ways**: the explicit `--live` flag; a keypair
  file supplied only through the `PROBE_KEYPAIR_FILE` environment
  variable; a fee cap present in the config (if the cap key is missing,
  live mode refuses to start); and a minimum main-wallet balance
  (9,000,000 lamports as shipped; adjusted to 2,000,000 for passes 2–3
  with the floats already deployed — §9.2 item j).
- **Keys live outside the code.** Keys are supplied via environment /
  read-only volume mount only, never read from the repository; the
  Docker build context was audited (`.dockerignore` excludes
  `*keypair*.json`, `.env`, `keys/`, `data/*.jsonl`, logs and caches; a
  COPY-layer grep finds no key material), and reports and logs contain
  only public keys.
- **Everything is logged.** Every attempted send is written to
  `data/send_log.jsonl` and `data/spend_ledger.jsonl` before/after
  broadcast, with signature, target, window, set, `send_seq`, price and
  local timestamp.
- **Unit tests**: `python3 -m tests.test_units` — **14/14 PASS**
  (2026-10-25), covering the analyzer's (slot, index) ordering, per-window
  breakdowns, window planning (rotation cutting, epoch-relative windows,
  never returning a started window, budget and disjointness), fee math,
  the ledger cap, keypair round-trip, and the burst builder's
  one-blockhash-per-path behaviour. The suite was re-run and passed
  14/14 after each of the two sender fixes in §9.2.

## 4. Background in brief — the road a transaction travels, and the stated rules

A Solana transaction has no waiting room. The leader schedule is computed
an epoch in advance and is public; leaders serve four consecutive slots.
Wallets, RPC nodes and validators forward transactions directly toward the
current and next leaders (Gulf Stream) over QUIC connections, where the
leader applies stake-weighted quality of service — the share of ingress
capacity a sender may use is proportional to the stake behind the node it
sends from. Inside the leader, the Transaction Processing Unit's fetch
stage receives packets, SigVerify checks signatures and removes
duplicates, and the **banking stage** executes transactions against
current state and records them, in order, into the block; the broadcast
stage merely publishes the banking stage's decisions. Everything this
project measures happened in the banking stage.

The three target families state three positions. **Agave** (and its
forks) documents the fee-density rule of §1: a central scheduler organises
verified non-vote transactions into a priority graph tracking account
conflicts, and selects by fee-per-compute-unit among non-conflicting
transactions; fees are local (competition is per-account), and since
SIMD-0096 (February 2025) 100% of priority fees go to the leader.
**Jito-Solana** shares that scheduler heritage but adds an off-chain block
engine that assembles bundles — atomic searcher transaction groups placed
by auction. Bundles and tips are excluded from this study by the brief;
the open question our Jito targets answer is how the *ordinary*
transaction stream is ordered by the inherited scheduler in production.
**Firedancer** (Jump's ground-up C reimplementation) schedules in a
dedicated *pack* tile that orders verified transactions and groups them
into conflict-free work for parallel execution tiles; whether its emergent
ordering matches Agave's fee-density rule, is stricter, or is closer to
arrival order is an empirical question — the one this campaign asks.
(Sources for this section are listed in the project notes; the claims are
background, and no conclusion in this report rests on them.)

## 5. Verifiability and reproducibility

**One command, no keys** — this demonstrates the full pipeline (schedule
resolution, live client check, block parsing and position extraction) and
sends nothing:

```bash
docker compose run --rm probe dry-run
```

**Reproducing the campaign** (deliberate; needs a funded probe wallet and
a keypair file outside the repo, mounted read-only):

```bash
PROBE_KEYPAIR_FILE=/keys/.probe_keypair.json \
  docker compose run --rm probe send --live --windows 3
PROBE_KEYPAIR_FILE=/keys/.probe_keypair.json \
  docker compose run --rm probe analyze
```

Without Docker: `pip install -r requirements.txt`, then
`python -m probe.cli <subcommand>` with the same arguments.

**How this campaign was actually executed (stated honestly).** All three
live passes were run with the host route —
`PROBE_KEYPAIR_FILE=<project dir>/.probe_keypair.json python3 -m probe.cli
send --live --windows 3`, followed by `python3 -m probe.cli analyze` —
because Docker cannot run inside the build sandbox used for this project
(§9.1 item 5: no iptables NAT module, runc namespace operations blocked).
The Dockerfile's exact steps were mirrored on the host Python 3.12
environment instead; the `docker compose` route above is the shipped
one-command path on any normal Docker host. The two sender fixes of §9.2
were applied between passes; the analyzer was never modified.

**Raw data shipped in this repo** (force-added at publication;
`.gitignore` excludes data files by default):

- `data/send_log.jsonl` — one record per attempted send: signature,
  target label, window start slot, set, `send_seq`, price
  (µL-per-CU), fee paid, local timestamp, status.
- `data/spend_ledger.jsonl` — every fee-bearing attempt, the input to the
  spend-cap accounting of §3.3.
- `data/analysis_*.json` — the analyzer's full output: `generated`
  timestamp; `summary` (per-target statistics, §6); and `records` — every
  probe with its recovered **slot** and **index within the block**. Three
  files are shipped: per-pass outputs after runs 1 and 2
  (`analysis_20261031T010526Z.json`, `analysis_20261031T012938Z.json`) and
  the canonical combined output
  (`analysis_20261031T014525Z.json`).
- Run console logs and run-time schedule/gossip checks:
  `data/live_run_console_20261031T005609Z.log` (run 1),
  `data/live_run2_console_20261031T011047Z.log` (run-2 gate refusal),
  `data/live_run2_console_20261031T011307Z.log` (run 2),
  `data/live_run3_console_20261031T013457Z.log` (run 3),
  `data/schedule_check_20261031T011033Z.log`,
  `data/schedule_check_20261031T013442Z.log`,
  `data/dry_send_check_20261031T013435Z.log`.
- `reports/ANALYSIS_SUMMARY.md` — the definitive combined statistics
  (per run, per validator, per run-time client), every number traced to
  the artifacts above.

**Independent verification.** For any probe: take its signature from
`data/send_log.jsonl`, fetch `getBlock` for its slot from
`data/analysis_*.json`, and find the signature's index in the block's
transaction list. It must equal the recorded `index`, and the relative
order of a window's probes so recovered must equal the order the analyzer
used. No claim in §6 or §8 rests on data a judge cannot re-derive this
way. The dry-run evidence for the pipeline itself (2026-10-25, slot
461,076,594, a real 540-transaction block parsed end-to-end) is in
`data/dry_run_20261025T014902Z.log`; the full pre-campaign verification
record is `reports/READINESS.md`.

**Where each number in §6 comes from** (all fields of
`data/analysis_20261031T014525Z.json` → `summary[]`, one entry per
target): measurement date ← the entry's probe timestamps in `records`
(cross-check `send_log.jsonl.ts`); client (live-verified) ← run-time
gossip attribution (§2) — note the analyzer's own `summary[].client`
carries the `validators.json` snapshot label, so for everstake_fd,
galaxy_fd and figment_harmonic the client shown in §6 is the run-time
value from §2, and `reports/ANALYSIS_SUMMARY.md` documents the
relabelling; windows ← distinct `window_start` values per target in
`records`; probes landed/sent ← `probes_landed_in_window` / `probes_sent`;
fee ρ ← `fee_set.spearman_price_vs_position`; arrival ρ ←
`arrival_set.spearman_sendorder_vs_position`; conflict pairs ←
`conflict_pairs` (each entry's `first_landed`); Kendall's τ for the fee
ladder ← `fee_set.kendall_price_vs_position`. Pooled per-client figures
(§6.2) were produced by running the analyzer's own `summarize()` function,
unmodified, on the canonical file's annotated records, relabelled with
the run-time attribution (§2); the construction is documented in
`reports/ANALYSIS_SUMMARY.md`.

## 6. Results

**Landing counts (all three passes combined).** 462 probes broadcast;
**42 landed in-window (9.1%)**, 308 landed outside their window within
the searched span, 112 were not found in the span. Per pass: run 1 —
176 sent, 10 in-window (5.7%), 123 outside, 43 never; run 2 — 132 sent
(plus 44 attempted but never broadcast, §9.2 item b), 22 in-window
(16.7%), 86 outside, 24 never; run 3 — 154 sent, 10 in-window (6.5%),
99 outside, 45 never. Every in-window landing in the dataset is a
fee-ladder probe (§9.2 item f); the arrival ladder landed in-window
**0 of 168** times and no conflict pair completed in-window (**0 of 42**
pairs). The statistics below are therefore fee-set statistics, with the
arrival and conflict questions explicitly unanswered — not zero-effect
results.

### 6.1 Per-validator ordering rule

All measurements are dated **2026-10-31** (runs at ≈ 00:56Z, ≈ 01:13Z,
≈ 01:35Z UTC); the date is the same in every row. "Windows" counts
executed windows across the three passes.

| Validator (operator) | Client (live-verified, run-time) | Windows | Probes landed in-window / sent | Fee rule — ρ price vs position (`fee_set`) | Arrival rule — ρ send-order vs position (`arrival_set`) | Conflict pairs — fee won / scored (`conflict_pairs`) | Conclusion |
|---|---|---|---|---|---|---|---|
| Kiln1 | JitoLabs 4.3.2 | 6 | 5 / 66 | **+1.0** (Kendall τ-b +1.0; fee n=5; one window with a per-window statistic: 463500964, n=3, +1.0) | **Not computable** — 0 in-window arrival landings (n=0) | 0 scored of 6 pairs attempted — **not computable** (no pair with both members in-window) | **H0** — no stable rule detectable at this probe scale (see reading below) |
| P2P.org | JitoLabs 4.3.2 | 5 | 2 / 55 | **0.0** (Kendall τ-b 0.0; fee n=2 pooled across two windows, one in-window fee probe each — the two probes tie in landed rank, so the pooled ρ is 0.0; no per-window statistic exists) | **Not computable** — 0 in-window arrival landings (n=0) | 0 scored of 5 pairs attempted — **not computable** | **H0** — no stable rule detectable at this probe scale |
| Everstake | JitoLabs 4.3.2 (run-time; snapshot said Firedancer 26.10.4) | 9 | 12 / 99 | **+1.0** (Kendall τ-b +1.0; fee n=12; per-window ρ +1.0 in all 4 windows with a statistic: n=2, 2, 2, 3) | **Not computable** — 0 in-window arrival landings (n=0) | 0 scored of 9 pairs attempted — **not computable** | **H0** — no stable rule detectable at this probe scale |
| Galaxy | Firedancer 26.10.5 (run-time; snapshot said 26.10.4) | 7 | 11 / 77 | **+1.0** (Kendall τ-b +1.0; fee n=11; per-window ρ +1.0 in all 3 windows with a statistic: n=4, 3, 3) | **Not computable** — 0 in-window arrival landings (n=0) | 0 scored of 7 pairs attempted — **not computable** | **H0** — no stable rule detectable at this probe scale |
| Figment | HarmonicAgave 4.4.0 (run-time; snapshot said 4.3.2) | 9 | 8 / 99 | **+1.0** (Kendall τ-b +1.0; fee n=8; per-window ρ +1.0 in all 3 windows with a statistic: n=3, 2, 2) | **Not computable** — 0 in-window arrival landings (n=0) | 0 scored of 9 pairs attempted — **not computable** | **H0** — no stable rule detectable at this probe scale |
| Coinbase 04 | HarmonicAgave 4.3.2 | 6 | 4 / 66 | **+1.0** (Kendall τ-b +1.0; fee n=4; one window with a per-window statistic: 463505604, n=2, +1.0) | **Not computable** — 0 in-window arrival landings (n=0) | 0 scored of 6 pairs attempted — **not computable** | **H0** — no stable rule detectable at this probe scale |

**Reading of the table (per §7's pre-registered rules, applied
mechanically).** H1 (fee-following) requires a *negative* fee ρ,
sign-consistent across windows: it is met nowhere — wherever the fee
statistic is computable it is +1.0 (or, for p2p_org's two cross-window
probes, 0.0). H2 (arrival-following) is defined on the arrival ladder,
which produced zero in-window observations, so H2's statistic does not
exist and H2 cannot be concluded either — even though the fee ladder's
own landed order preserved its send order exactly in every observed
window, that observation is not the pre-registered H2 test (and within
the fee set, send order and price order are collinear by construction,
§3.2). The mechanical conclusion for all six validators is therefore
**H0: no stable rule detectable at this probe scale** — with the
specific, data-backed content stated in §8: no fee-following reversal
was observed in-window at any of the four price points, and the arrival
and conflict questions returned no in-window evidence at all.

Per-window detail (the sign-consistency evidence) is in
`data/analysis_20261031T014525Z.json` under `fee_set.per_window[]` and
`arrival_set.per_window[]` (each entry: `window_start`, `n`,
`spearman`), and is tabulated per validator and per pass in
`reports/ANALYSIS_SUMMARY.md`. Probes that landed outside their target's
window and probes that never landed are counted per target in the
analysis output (`probes_landed_outside_window`, `probes_never_landed`)
and discussed in §8 and §9.2.

### 6.2 Pooled per client family

Pooling uses the **run-time** attribution of §2 (the analyzer's snapshot
grouping differs for everstake_fd; see §5). The design's nominal pooled
sizes (fee n=24, arrival n=24, conflict n=6 per family) were **not**
reached; the effective sizes below are the landed in-window counts and
govern every reading.

| Client family (run-time) | Validators pooled | Fee ρ (effective n) | Arrival ρ (effective n) | Conflict fee-wins (scored pairs) | Reading |
|---|---|---|---|---|---|
| JitoLabs (Jito-Solana) | kiln1, p2p_org, everstake_fd — sent 220, in-window 19 | **+1.0** (n=19; Kendall τ-b +1.0; 5 windows with a per-window statistic, all +1.0, per-window n = 2, 2, 2, 3, 3) | **Not computable** (n=0 — zero in-window arrival landings in 168 arrival probes campaign-wide) | 0 scored of 20 pairs attempted — **not computable** | No fee-following observed in-window; landed order matched send order in all 5 scored windows. H0 at family level. |
| Firedancer | galaxy_fd only — sent 77, in-window 11 | **+1.0** (n=11; Kendall τ-b +1.0; 3 windows with a per-window statistic, all +1.0, per-window n = 4, 3, 3) | **Not computable** (n=0) | 0 scored of 7 pairs attempted — **not computable** | No fee-following observed in-window; landed order matched send order in all 3 scored windows. H0 at family level. This family rests on a single validator at run time (§2). |
| HarmonicAgave | figment_harmonic, coinbase04_harmonic — sent 165, in-window 12 | **+1.0** (n=12; Kendall τ-b +1.0; 4 windows with a per-window statistic, all +1.0, per-window n = 3, 2, 2, 2) | **Not computable** (n=0) | 0 scored of 15 pairs attempted — **not computable** | No fee-following observed in-window; landed order matched send order in all 4 scored windows. H0 at family level. |

**Reduced sample sizes (complete statement).** The design planned, per
validator, fee n=12 / arrival n=12 / conflict 3 pairs and, pooled per
family, fee n=24 / arrival n=24 / conflict 6 pairs. Effective in-window
sizes are: fee — kiln1 5, p2p_org 2, everstake_fd 12, galaxy_fd 11,
figment_harmonic 8, coinbase04_harmonic 4 (family pools: JitoLabs 19,
Firedancer 11, HarmonicAgave 12); arrival — **0 for every validator and
every family**; conflict — **0 scored pairs for every validator and
every family** (42 pairs attempted). The cause is the landing pattern of
§9.2: bursts fired through public RPC mostly reached leaders at or after
their 4-slot windows closed, and only the head of each burst (the fee
ladder, sent first) ever landed in-window.

## 7. Analysis — interpretation rules (pre-registered)

These rules were fixed in `DESIGN.md` before any live send and are
applied mechanically; they are stated here so a judge can re-derive every
conclusion in §6 from the raw output.

- **Position and ranks.** A probe's landed position is its index within
  its block; ordering across a window's slots is by **(slot,
  index-in-block)**, chronological across the window. Statistics use
  window-relative ranks of our own probes only.
- **Execution order.** Within a window the sender builds and signs all 11
  probes up front (one blockhash per RPC path) and fires them in the
  recorded `send_seq` order with the configured gaps; across targets and
  windows, execution is **chronological by window**, and windows whose
  start has passed are skipped, never fired late. `send_seq`, intended
  price and local send timestamps are in the send log for every probe.
- **Sign conventions.** Fee-following ⇒ landed rank improves as price
  rises ⇒ `spearman_price_vs_position` **negative** (strong fee-following:
  ρ ≈ −0.8 or better at family level). Arrival-following ⇒ earlier-sent
  probes land earlier ⇒ `spearman_sendorder_vs_position` **positive**.
  The fee ladder is sent cheapest-first precisely so the two rules make
  opposite predictions on the same data.
- **Evidence FOR a fee rule** (per validator): negative fee ρ with the
  **same sign in all 3 windows** (`fee_set.per_window[].spearman`), i.e.
  the cross-window sign-consistency bar of `DESIGN.md`. Evidence AGAINST:
  fee ρ ≈ 0, inconsistent signs across windows, or a fee effect that
  appears only in a single window.
- **Evidence FOR an arrival rule**: positive arrival ρ, sign-consistent
  across windows, in the absence of a consistent fee effect. Evidence
  AGAINST: arrival ρ inconsistent across windows, or arrival order that
  survives only when all prices are equal (the arrival ladder) but is
  overridden whenever prices differ (the fee ladder) — that pattern is
  fee-following with arrival as a tiebreak, and is reported as such.
- **Conflict pairs.** A pair is a fee-win when the 250,000-µL/CU member
  lands in the earlier serial position (`conflict_pairs[].first_landed`).
  Per family (n=6): 6/6 fee-wins ⇒ p ≈ 0.016 under a fair-coin null
  (evidence); 5/6 ⇒ p ≈ 0.11 (suggestive only, reported as such);
  anything less is no detectable fee priority inside conflict chains at
  this scale. **As executed, no pair could be scored (0 complete
  in-window pairs), so this rule was never applied — the conflict
  question is unanswered, not answered negatively.**
- **The path control** bounds the road-vs-scheduler confound: if the
  path-control probe's landed rank (via the alternate RPC) deviates
  systematically from what its price predicts in the main-path ladders,
  the affected window's reading is downgraded and the deviation is
  reported in §8. **Outcome (from the analysis records): the
  path-control probes produced no in-window landings at all — 0 of 42.
  16 of the 42 landed within the searched span, all outside their
  windows, at offsets 5–17 slots after window end (median 7), versus
  the primary path's outside landings at a median of 5 slots; the
  remaining 26 were not found in the span. No in-window deviation can
  therefore be assessed; the quantified endpoint difference (the
  alternate path's landings are systematically later) is reported in §8
  as a property of the submission path, not of any scheduler.**
- **Null results.** Where neither rule meets its bar, the conclusion is
  H0 — "no stable rule detectable at this probe scale" — stated as a
  conclusion with the raw data attached, per the listing's analysis
  criteria. No conclusion in §6 may claim more than §8's limitations
  allow: in particular, no fee *threshold* finer than the ladder spacing,
  and no load-dependence claim.

## 8. Findings

### 8.1 JitoLabs family — kiln1, p2p_org, everstake_fd (run-time attribution)

**Conclusion: H0 for all three validators** — no stable rule detectable
at this probe scale, by the mechanical application of §7.

The numbers: pooled over the three validators (220 sent, 19 in-window),
the fee ladder's Spearman ρ (price vs landed position) is **+1.0** at
n=19 (Kendall τ-b +1.0). Per validator: everstake_fd +1.0 (n=12),
kiln1 +1.0 (n=5), p2p_org 0.0 (n=2 — two single in-window fee probes in
two different windows, tied in landed rank, hence the 0.0 pooled value;
no per-window statistic exists for p2p_org). Five windows carry a
per-window fee statistic (per-window n = 2, 2, 2, 3, 3) and all five are
+1.0: in every window where in-window fee order is observable at all, the
landed order is exactly the send order, cheapest first — the opposite of
the fee-density prediction of §4. The arrival ladder produced zero
in-window landings for all three validators, and no conflict pair
completed in-window (20 pairs attempted), so neither H2 nor the
conflict sub-question could be tested for this family.

Strictness: the "no fee-following" statement is exact within its sample
— not one of the 19 in-window fee probes landed ahead of a cheaper probe
sent before it — but the sample grain is coarse: at per-window n=2,
Spearman ρ can only be ±1 or 0, so the consistency count (5/5 windows)
carries less weight than the pooled n=19 exact-order observation, and
both are stated at that strength and no further.

Path control: no path-control probe landed in-window for any validator
in this family (nor anywhere else; §7). Family-specific qualification:
everstake_fd is in this family only because of its run-time gossip
attribution (JitoLabs 4.3.2); under its 2026-10-25 snapshot label it
would have been pooled as Firedancer, which is why §6.2 documents the
relabelling. p2p_org broadcast nothing in run 2 (one window skipped,
two lost to blockhash expiry, §9.2 items b/d). Never-landed counts are
the family's highest (everstake_fd 29, p2p_org 20, kiln1 13 of their
sent probes were not found in the searched span).

### 8.2 Firedancer family — galaxy_fd (only validator at run time)

**Conclusion: H0** — no stable rule detectable at this probe scale.

The numbers: galaxy_fd sent 77 probes, 11 landed in-window, all in the
fee set. Fee ρ is **+1.0** at n=11 (Kendall τ-b +1.0), with a per-window
statistic in 3 windows (n = 4, 3, 3 — the largest per-window samples in
the dataset) — all +1.0. As with JitoLabs, landed order matched send
order exactly wherever it was observable; no fee-following reversal
appeared at any rung. Arrival ρ is not computable (0 in-window arrival
landings) and 0 of 7 conflict pairs completed in-window.

Strictness and qualification: run 2 was this validator's strongest pass
(10 of its 11 in-window landings, in-window share 30.3% for that pass),
and run 3 produced none — the family reading therefore leans heavily on
one pass. The structural weakness is stated plainly: at run time this
"family" is a **single validator** (everstake_fd, planned as the second
Firedancer target, reported JitoLabs 4.3.2 in gossip at every run-time
check). Nothing in this section should be read as a characterisation of
Firedancer-the-client beyond galaxy_fd's windows on 2026-10-31. The
path-control outcome for galaxy_fd matches the campaign-wide picture
(no in-window control landing; the alternate path's landings were
systematically later, §7).

### 8.3 HarmonicAgave family — figment_harmonic, coinbase04_harmonic

**Conclusion: H0 for both validators.**

The numbers: pooled, 165 sent and 12 in-window; fee ρ **+1.0** at n=12
(Kendall τ-b +1.0), with per-window statistics in 4 windows
(n = 3, 2, 2, 2), all +1.0. Per validator: figment_harmonic +1.0 (n=8;
run-time version HarmonicAgave 4.4.0, against the 4.3.2 snapshot) and
coinbase04_harmonic +1.0 (n=4; a single scored window, n=2).
coinbase04_harmonic landed nothing in-window in run 1 (0 of 22) and had
one run-2 window lost to blockhash expiry (§9.2 item b). Arrival ρ is
not computable (0 in-window landings) and 0 of 15 conflict pairs
completed in-window.

Strictness: identical in form to the other families — exact
send-order preservation in every scored window, at coarse per-window
grain; the pooled n=12 exact-order observation is the evidentiary core.
Path control: no in-window control landing for either validator
(campaign-wide pattern, §7).

### 8.4 Cross-family synthesis

Measured against the documented rules of §4, the campaign's results are:

1. **The documented Agave fee-density rule was not observed in-window —
   in any of the three families.** In all 42 in-window landings (all
   fee-ladder probes) across 12 windows with a computable statistic,
   landed order followed send order exactly (ρ = +1.0, sign-consistent
   12/12); the single non-+1.0 pooled value in the dataset is
   p2p_org's 0.0, an artifact of two probes pooled across windows
   (§6.1). No window, validator or family shows the negative ρ that
   fee-following predicts at the tested price points (0 / 10k / 50k /
   250k µL-per-CU). This is reported at exactly the strength §7 allows:
   it is evidence that *in these windows, at these price points, with
   this submission path*, ordering did not follow fee density. Given
   the sample grain (per-window n of 2–4) and the selection effect of
   §9.2 item f, it is **not** evidence that these schedulers never
   order by fee.
2. **The arrival-order and conflict-chain questions are unanswered.**
   Zero in-window observations for both sets (0/168 arrival probes,
   0/42 complete conflict pairs) means the dataset contains no evidence
   about either — stated as "not measured", per this report's rules,
   not as a negative result.
3. **The dataset's robust, high-n finding is about the submission
   path, not the schedulers.** Across 462 broadcasts, 90.9% of probes
   missed their 4-slot target windows despite two successive timing
   fixes that each eliminated the previous pass's dominant failure mode
   (run 1 lateness → run 2 in-window share 16.7%; run 2 blockhash
   expiry → run 3 zero send-layer losses). In-window landings cluster
   at the **end** of windows (offsets +1…+3 slots from window start,
   median +3; none at offset 0), and outside-window landings fall a
   median of 5 slots after window end. With bursts fired at
   window-start − 2 slots through public RPC, the bursts predominantly
   reached leaders at or after the windows closed — and only their
   earliest sends (the fee ladder) ever made the tail of a window.
   Any future measurement of scheduler rules at this window size needs
   a materially lower-latency submission path (raw-QUIC TPU submission,
   explicitly declined in this design — §10) before it needs more
   probes.

## 9. What went wrong

### 9.1 Pre-campaign incidents (design, rehearsal and verification — all dated 2026-10-25, all before any mainnet send)

1. **Signature-collision hazard in the probe construction.** Fee-ladder
   and arrival transactions built from the same accounts under one
   blockhash would have been byte-identical — the same signature — and
   the second could never have landed; a rung-0 "result" would have been
   an artifact of deduplication, not of any scheduler. Caught during
   design verification, before any live send. Fixed by construction:
   the transfer amount carries a 1–11 lamport dust nonce encoding the
   send sequence, so every probe is unique on the wire (`probe/plan.py`;
   the disjointness and budget properties are unit-tested).
2. **Zero-lead window planning.** The planner could return windows with
   no usable planning lead — windows already effectively starting —
   which would have meant firing late or not at all. Found in the
   local-cluster rehearsal and fixed: planning enforces
   `min_window_lead_slots` (default 75 ≈ 30 s) and never returns a
   window that has already started (unit test:
   `test_next_windows_never_returns_started_window`).
3. **Epoch-length windows for long leader runs.** The planner initially
   treated a long leader run as one window; fixed by cutting runs into
   rotation-sized (≤ 4-slot) windows aligned to the run start
   (unit tests: `test_next_windows_cuts_long_runs_into_rotations`,
   `test_next_windows_epoch_relative`).
4. **Keypair material reachable by the Docker build context.** An early
   build-context audit found keypair files were not yet excluded from
   the image build context. Fixed with `.dockerignore` (excludes
   `*keypair*.json`, `.env`, `keys/`, `data/*.jsonl`, logs and bytecode
   caches) and re-audited: a COPY-only build + filesystem export and a
   COPY-layer grep confirm the shipped context contains code, configs
   and docs, and no key material. `keys/` is mounted read-only at
   runtime and gitignored.
5. **Full container run could not be executed in the build sandbox.**
   The sandbox kernel lacks the iptables NAT module (bridge networking
   fails) and blocks the namespace operations runc needs
   (`setns: operation not permitted`), so `docker compose build` +
   `docker compose run` could not be run end-to-end there. This is a
   property of that sandbox, not of the image: the Dockerfile's exact
   steps (`pip install -r requirements.txt`, then
   `python -m probe.cli dry-run`) were mirrored in a clean virtualenv on
   the host Python 3.12 and completed successfully
   (`data/dry_run_20261025T014902Z.log`), and `docker compose config`
   parses the shipped compose file. On any normal Docker host the
   one-command run is `docker compose run --rm probe`.
6. **Devnet/testnet rehearsal path unavailable.** On 2026-10-25 the
   devnet faucet was dry from this network (`requestAirdrop` returned
   429 at 2 / 1 / 0.1 SOL) and testnet returned −32603 internal errors,
   so the suggested devnet end-to-end rehearsal could not be funded.
   The devnet pipeline (alternative validators/config) was prepared and
   removed afterwards; the repo stays mainnet-focused.
7. **Local test-validator never executes transactions.** The full live
   path was rehearsed against a local `solana-test-validator` (v2.3.13;
   the v4.3.2 validator panics in that sandbox because io_uring is
   blocked): preconditions, planning, setup transfers (built, signed,
   accepted by RPC) and an 11-probe burst all ran, and the probe whose
   payer existed executed its full instruction path in simulation
   (ComputeBudget + System program success, 450 CU). Landing itself
   could not be demonstrated: that validator never executes **any**
   transaction — proven environmental with the official Solana CLI as a
   control (its transfer was likewise accepted and never confirmed).
   Landing is a property of the cluster, not of the transactions; the
   identical build/send path is exercised by the unit tests against a
   reference block parser.

### 9.2 Live-run incidents (all 2026-10-31, UTC)

The campaign was **not** uneventful. Every deviation from `DESIGN.md`
is recorded here; the engineering record with full detail is
`reports/READINESS.md` (dated addenda per pass), and the definitive
statistics are `reports/ANALYSIS_SUMMARY.md`.

**(a) Run 1 — burst lateness (blockhash fetch + signing after the
wait).** Run 1's executor waited for the window trigger first and only
then fetched blockhashes and built/signed the bursts; the two public-RPC
round-trips after the wait pushed whole bursts several slots late. Of
176 probes sent, only **10 landed in-window (5.7%)** — all 10 at offset
+3, the last slot of their 4-slot windows — while the 123
outside-window landings fell 1–8 slots after window end (median 5 slots
≈ 2 s). *Fix applied before run 2:* build and sign all 11 transactions
**before** the wait (safe within a blockhash's ~150-slot validity given
the ≥75-slot planning lead); unit suite 14/14 after the change, and a
dry-run pass verified byte-identical logs. Run 2's in-window share rose
to 16.7%.

**(b) Run 2 — BlockhashNotFound losses (44 probes, 4 windows, never
broadcast).** The run-1 fix created the opposite failure: bursts are
now built before the wait, so later-queued windows whose turn came more
than ~150 slots after their build reached the burst holding an expired
blockhash. In 4 windows — p2p_org 463500264, p2p_org 463500740,
kiln1 463501236, coinbase04_harmonic 463502600 — **all 44 probes**
failed simulation with RPC −32002 after 4 tries each (40 recorded as
`BlockhashNotFound`, 4 as `Blockhash not found` — the same failure in
two RPC message formats) and were **never broadcast; no fees were
charged on-chain for them**. p2p_org consequently broadcast nothing at
all in run 2.

**(c) The freshness mechanism that resolved it (run 3).** Before run 3,
`execute_window` was changed to record, per RPC path, the chain slot at
which that path's blockhash was fetched, and at burst time to re-fetch
and re-sign **once** for any path aged more than 100 slots
(`BLOCKHASH_MAX_AGE_SLOTS = 100`, a safety margin under the ~150-slot
validity); fresh paths fire exactly as built. Verified by the unit
suite (14/14) and a scripted fresh/stale functional check (stale path
re-signed with a fresh blockhash; fresh path byte-identical). **Run 3
result: 154/154 probes broadcast, zero send errors, zero blockhash
losses — the failure did not recur**, including in the late-queued
windows (e.g. p2p_org 463506560, everstake_fd 463506672) that have the
run-2 failure shape.

**(d) Skipped windows (never-fire-late rule).** Of 54 planned windows
(18 per pass), 8 were skipped because the window had already started
when its turn came — run 1: 2 (coinbase04_harmonic 463494856,
galaxy_fd 463495000); run 2: 2 (p2p_org 463500084,
coinbase04_harmonic 463501396); run 3: 4 (kiln1 463505952,
p2p_org 463505968, kiln1 463506052, galaxy_fd 463506104) — for a total
of **2 + 2 + 4 = 8 skipped** and 42 windows executed (16 + 12 + 14,
where run 2's 12 counts only fully-broadcast windows; 4 further run-2
windows were attempted and lost per item b). Skipped windows were never
fired late, per the pre-registered rule.

**(e) Arrival ladder and conflict pairs — both unanswered.** The
arrival ladder landed in-window **0 times in 168 probes** (133 landed
outside their window within the searched span, 35 were not found in
the span); the analyzer returns n=0 and ρ=null everywhere for this
set. Conflict pairs: 84 probes (42 pairs) were sent, and **no window
in any pass has both members landed in-window (0 complete pairs)**, so
no conflict outcome exists. (Records-level observation, not an
analyzer statistic: both members landed somewhere in the wider
searched span in 17 windows — never both inside the target window.)
Both pre-registered sub-questions are therefore **unanswered by
in-window data** and are reported as "not measured" throughout this
report; nothing in §6 or §8 claims an arrival or conflict effect in
either direction.

**(f) Selection effect in the in-window sample (disclosed).** All 42
in-window landings are fee-set probes — the first four sends of each
11-probe burst. The fee ladder is sent first in every burst, so the
only probes that ever caught the tail of a window are fee-ladder
probes. Every ordering statistic in this report is therefore computed
on the head of each burst; the dataset contains no in-window evidence
about how the later burst positions (arrival, conflict, control) would
have been ordered had they arrived in time.

**(g) Small per-window samples behind the sign consistency.** The
12/12 sign consistency of the fee statistic (§6) rests on per-window
samples of n=2–4 landed probes. At n=2, Spearman's ρ is ±1 by
construction; at n=3–4 it takes only coarse values. The consistency
count is reported because §7 pre-registers it, but the evidentiary
weight sits in the pooled exact-order observations (n=19/11/12 per
family), and both are stated at that strength in §8.

**(h) Price/send-order collinearity.** By design (§3.2), the fee
ladder is sent cheapest-first, so price order and send order are
identical within the fee set and their two ρ's are necessarily equal;
the fee set alone cannot attribute the preserved order to "arrival"
rather than to "price irrelevance". The design's discrimination rests
on the sign (fee-following would have produced a *negative* ρ) and on
the arrival ladder as the independent arrival test — which returned
no data (item e). This caveat from `DESIGN.md` is restated here
because it bounds every reading of §6.

**(i) All three passes ran on one morning.** Runs 1–3 were executed on
2026-10-31 between 00:56Z and 01:40Z, across distinct leader rotations
but within a single ~45-minute span of network conditions. `DESIGN.md`
intended windows "spread across the campaign days" so that a single
machine/network state cannot masquerade as a rule; the distinct-
rotations property holds, the across-days property does not. This is
a deviation from the design intent and is carried as a limitation in
§11: the results characterise these validators on that morning, not
across days or load regimes.

**(j) Funding-gate adjustment (operator decision, between runs 1 and
2).** After run 1, the main account held 3,496,600 lamports — below
the shipped `min_wallet_balance_lamports` of 9,000,000 — and the first
run-2 invocation was **refused by the tool's own funding gate** (exit
code 2, 2026-10-31T01:10:47Z; zero transactions sent, zero fees spent,
logs byte-identical after the attempt; console:
`data/live_run2_console_20261031T011047Z.log`). The 9,000,000 figure
was derived for a *fresh* campaign: it covers deploying 7,636,160
lamports of sender floats plus the main account's own fees and
headroom. For a second pass the floats are already deployed (run 1
left them in the 7 sender accounts), so the gate as written
double-counts capital already in place; the true marginal cost of a
further pass is ≤ ~1.2M lamports (top-up shortfalls ≈ ≤800K, main's
own probe fees ~160K, funding-transfer fees ≤ ~175K), and the main
account held ≈ 3× that. The operator therefore lowered the single
config value `min_wallet_balance_lamports` from **9,000,000 to
2,000,000** for passes 2–3. Nothing else in the config changed; the
cumulative spend cap (10,000,000 lamports) was **not** altered, and
the unit suite passed 14/14 after the change. The full reasoning is
recorded in `reports/READINESS.md` (addendum, 2026-10-31).

**(k) Fee accounting — the ledger total is an upper bound.** The spend
ledger books each probe's planned fee at attempt time. Run 2's ledger
probe figure (889,120 lamports) therefore includes the planned fees of
the 44 never-broadcast probes of item (b), which were **not** charged
on-chain. The cumulative ledger total of **2,986,220 lamports** is
thus a conservative upper bound on true on-chain fees; the
cap-enforcement semantics (count every attempt) are unchanged and
deliberate. On-chain main-account balances (12,000,000 → 3,496,600 →
2,617,611 → 1,876,581 lamports, the last at slot 463,506,723) are
RPC-verified and reconcile with the transfers the main account
actually paid (§3.3; per-pass reconciliations in
`reports/READINESS.md`). Sender floats remain deployed in the 7 sender
accounts; the end-of-campaign sweep has not been performed.

*Postscript (2026-10-31): the end-of-campaign sweep was performed later on 2026-10-31 — all sender floats were swept to main and 8,309,671 lamports were returned to the operator's personal wallet; see the "Teardown — COMPLETED" addendum in `reports/READINESS.md` for per-transfer amounts and signatures.*

**Client-attribution changes (recorded per §2's rule).** At every
run-time gossip check, everstake_fd reported JitoLabs 4.3.2 (snapshot:
Firedancer 26.10.4), galaxy_fd reported Firedancer 26.10.5 (snapshot:
26.10.4) and figment_harmonic reported HarmonicAgave 4.4.0 (snapshot:
4.3.2). No target substitution was made; §6 pools by the run-time
values, and the Firedancer family consequently rests on galaxy_fd
alone (§8.2).

**Landing-pattern record (context for §8.4).** In-window landings
(n=42) sit at offsets +1…+3 slots from window start (median +3; none
at offset 0). Outside-window landings (n=308) fall 1–17 slots after
window end (median 5). Per pass, outside-offset medians: run 1 = 5
(n=123, max 8), run 2 = 4 (n=86, max 17), run 3 = 5 (n=99, max 8).

## 10. Brief-topics compliance — what the listing asked the README to address

The listing requires the README to address each topic below, or explicitly
decline it with reasons. The README addresses the first six in its design
section; this table is the report-side index, including the declines.

| Topic required by the listing | Where addressed | Position |
|---|---|---|
| Leader schedule and leader types | README ("Leader schedule and leader types"); this report §3.1, §2 | Addressed: published schedule, 4-slot runs, whole-window targeting with minimum lead; leader types = the three client families of §2. |
| The path of a transaction from backend to executing node, and everything in between | README ("The path of a transaction"); this report §4 | Addressed: Gulf Stream forwarding, QUIC stake-weighted QoS, TPU fetch → SigVerify → banking → broadcast; our probes travel this path via public RPC. |
| Interaction of our own transactions with each other | README ("Interaction of our own transactions"); this report §3.2 | Addressed: account-disjoint ladders by construction; the conflict pair is the single deliberate exception; dust-nonce uniqueness. |
| Competition inside the block | README ("Competition inside the block"); this report §3.4 | Addressed: only relative order of our own probes is used; background load cannot manufacture a signal. |
| Send order | README ("Send order"); this report §3.2, §7 | Addressed: fully recorded (`send_seq`, prices, timestamps); fee ladder sent cheapest-first so the candidate rules predict opposite orders. |
| Noise vs rule | README ("Noise vs rule"); this report §1, §7 | Addressed: pre-registered sign-consistency rule across 3 windows per validator; H0 ("no stable rule at probe scale") is a legitimate, reportable conclusion. |
| Jito validators in scope; bundles and tips out of scope | This report §2, §4 | Followed: two Jito-Solana targets measured on their ordinary transaction stream only. **Bundles/tips analysis explicitly declined** — the brief excludes them as a separate mechanism from the leader's scheduler. |
| Alpenglow boundary (measurements never mixed across 2026-10-21) | This report, header and §2 | Followed: all targets selected after the upgrade, all measurements taken after it, no pre-upgrade data exists in this project. |
| Raw-QUIC / TPU submission for full scheduler-vs-path separation | README ("What this design does NOT separate"); this report §11 | **Explicitly declined**: out of scope for this design. The RPC-path confound is bounded by the path-control probe, not eliminated (§11). |
| Frankendancer targets | This report §2 | **Declined, with reason**: Frankendancer is unsupported under Alpenglow and no longer exists on mainnet; the third family measured is the full Firedancer client. |
| Block-fullness / load as an experimental factor | README ("What this design does NOT separate") | **Declined, with reason**: load is recorded as context, not manipulated; the design holds no lever over block fullness. |
| Fee thresholds finer than the ladder spacing | This report §11 | **Declined, with reason**: 4 rungs resolve fee effects at 4 price points; finer thresholds are not measurable with this design and are not claimed. |

## 11. Limitations

- **RPC-path vs scheduler separation is bounded, not eliminated.** The
  two RPC paths are two endpoints into the same public infrastructure,
  not two network routes into the leader; the path control bounds the
  confound but cannot remove it. Full separation would need raw-QUIC
  TPU submission, which is out of scope (and Jito bundles/tips are
  excluded by the brief anyway).
- **Gossip `clientId` is self-reported** by each validator; a
  mislabelled client would blur the client-family comparison.
  Attributions are cross-checked against version strings and public
  registries at selection time, and re-read live at campaign time, but
  they are not proven.
- **Four fee rungs only.** The ladder resolves fee effects at 0 / 10k /
  50k / 250k µL-per-CU; a fee *threshold* finer than that spacing cannot
  be located with this design and is not claimed.
- **Three windows per validator is a rule-detection sample, not a
  characterisation.** It can establish a sign-consistent direction (the
  pre-registered bar) but cannot characterise how a rule varies with
  load, time of day, or block fullness — none of which this design
  manipulates.
- **Scope.** Conclusions cover the six target validators, on the dates
  measured, on their ordinary transaction stream. Nothing is claimed
  about other validators, other dates, or bundle/block-engine behaviour.
- **One morning, one network state.** As executed, all passes ran on
  2026-10-31 within ≈ 45 minutes (§9.2 item i). The results do not
  characterise behaviour across days, epochs, or load regimes.
- **Selection effect in the evidence.** Every in-window ordering
  observation comes from the head of a burst (the fee ladder, §9.2
  item f). The arrival, conflict and path-control sets have no
  in-window observations at all; any statement about how these
  schedulers treat those transaction shapes is outside this dataset.
- **Coarse per-window statistics.** Per-window Spearman samples of
  n=2–4 take only coarse values (n=2 forces ρ=±1). Family readings rest
  on the pooled exact-order observations (n=11–19), themselves limited
  to the fee set.
- **Firedancer coverage is one validator.** At run time only galaxy_fd
  reported a Firedancer client (§2); the family column in §6.2 is a
  single-validator result wearing a family label, and is read as such
  in §8.2.
- **Fee totals are ledger upper bounds.** The spend-ledger totals
  (§3.3) include planned fees for 44 never-broadcast probes (§9.2
  item k); on-chain fees are lower. Cap compliance is unaffected (the
  ledger is the cap's own accounting).

## 12. Conclusion

Across six production validators spanning the three post-Alpenglow
client families, the pre-registered verdict is the same for every
validator and every family: **H0 — no stable ordering rule is
detectable at this probe scale**. That verdict has specific content,
not just an absence: wherever in-window fee order was observable at
all (42 probes, 12 windows, pooled n=19/11/12 per family), the landed
order preserved the send order exactly (Spearman ρ = +1.0, Kendall
τ-b = +1.0), and **fee-following — the negative ρ the documented
fee-density rule predicts — was never observed at any of the four
price points**. The arrival-order and conflict-chain questions
returned no in-window evidence whatsoever and are reported as not
measured.

Against the documented rules of §4, production behaviour therefore
neither confirms the Agave fee-density description nor refutes it: the
measurement's discriminating power was consumed by the submission
path. The campaign's firmest result is a measurement of that path
itself — with bursts fired through public RPC at 4-slot leader
windows, 90.9% of 462 probes missed their windows despite two
successive, verified timing fixes, in-window landings cluster at
window tails, and only the head of each burst ever arrived in time.
Where the honest answer is noise, this report says noise; where the
sample is thin, it says how thin; and the two sub-questions the data
cannot answer are named, not papered over.

What remains is the deliverable itself: a reproducible ruler — the
probe tool (dry-run by default, live only behind an explicit flag
under a code-enforced spend cap), the complete raw signatures and
slots in `data/`, and the pre-registered decision rules of §7 — that
anyone can apply to the next validator, the next client release, and
the next upgrade, and whose every number in this report can be
re-derived from `getBlock` by any judge.
