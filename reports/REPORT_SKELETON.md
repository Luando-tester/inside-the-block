# Inside the Block — measurement report (SKELETON, pre-written 2026-10-27)

> **Status of this document.** Every section that does not depend on live
> mainnet measurements is written completely and finally. Every spot that
> depends on the live campaign is marked **[FILL AFTER RUN: …]** with the
> exact value required and the exact analyzer/send-log field it comes from.
> No measurement, number, or result has been invented: every quantitative
> claim below is taken from `DESIGN.md`, `config.json`, `validators.json`,
> `reports/READINESS.md`, or the shipped code, and is checkable against
> them. When the campaign completes, fill the placeholders, delete this
> status box and the completion checklist, and this file becomes the
> submission report.

## Completion checklist — what remains after funding lands

- [ ] **Fund the probe wallet**: send **0.009 SOL** (from free-bounty
      winnings, per the operator's rule) to the probe wallet's main account
      `CAtqKwVaYbZqB33sLNvsKNpr7Y8BnZf3X6V4PCjHrP2v`. Live mode refuses to
      start below `min_wallet_balance_lamports` = 9,000,000 lamports.
      Funding target date ≈ 2026-11-02/03 (leaves ≥ 2 days for measuring
      and reporting).
- [ ] **Place the keypair file** in `./keys/` (gitignored, mounted
      read-only) or any path outside the repo; it is referenced only via
      the `PROBE_KEYPAIR_FILE` environment variable and is never committed.
- [ ] **Live run**:
      `PROBE_KEYPAIR_FILE=/keys/.probe_keypair.json docker compose run --rm probe send --live --windows 3`
      (or per-target occasions: `send --live --target <label> --windows 1`).
- [ ] **Analyze**:
      `PROBE_KEYPAIR_FILE=/keys/.probe_keypair.json docker compose run --rm probe analyze`
      → produces `data/analysis_*.json`.
- [ ] **Fill every [FILL AFTER RUN] placeholder** in this file from the
      analysis JSON / send log (each placeholder names its source field),
      and complete §9.2 (live-run incidents) — if the campaign was
      uneventful, state that explicitly; the section may not be left blank
      by omission.
- [ ] **Publish the repo**: force-add the raw data
      (`git add -f data/*.jsonl`) — `.gitignore` excludes data files by
      default, but the brief requires all signatures and slots in the repo.
      Confirm the keypair file is **not** in the repo.
- [ ] **Submit (human-account action)**: the operator submits the public
      repo link + this report on Superteam Earn from their own account
      before **2026-11-05T21:59:59Z** (≈ 04:59 on 2026-11-06, Asia/Saigon).
      The listing is HUMAN_ONLY; agent API submissions are rejected (403).

---

# Inside the Block: How Solana Validators Order Transactions

**Bounty:** Superteam Earn — "Inside the Block: How Solana Validators
Order Transactions", sponsored by Superteam Ukraine, published
2026-10-22.
**Listing:** https://earn.superteam.fun/listing/inside-the-block-how-solana-validators-order-transactions/
**Network:** Solana Mainnet only.
**Alpenglow side:** after — the upgrade activated on mainnet on
2026-10-21; every measurement in this report was taken after it, and no
pre-upgrade data exists in this project or is pooled with these results.
**Campaign dates:** [FILL AFTER RUN: campaign start and end dates (UTC),
from the first and last `ts` values in `data/send_log.jsonl`]
**Probe wallet (public):** `CAtqKwVaYbZqB33sLNvsKNpr7Y8BnZf3X6V4PCjHrP2v`
**Total fees spent:** [FILL AFTER RUN: total lamports from
`data/spend_ledger.jsonl`] of the 10,000,000-lamport (0.01 SOL)
code-enforced cap.
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
reported as suggestive only).

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
fired late. Each validator is measured in **3 windows on separate
occasions** (different leader rotations, spread across the campaign), so a
single machine state cannot masquerade as a rule.

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

### 3.3 Campaign shape and spend

6 validators × 3 windows × 11 probes = **18 windows, 198 probe
transactions**. Fees per window are fully determined by the construction:
fee ladder 20,310 + arrival ladder 20,000 + conflict pair 10,250 + path
control 5,010 = **55,570 lamports per window**, hence campaign probe fees
of **1,000,260 lamports**. Setup transfers add ≈ 35,000 lamports per
top-up occasion (7 × 5,000). The **code-enforced spend cap is 10,000,000
lamports (0.01 SOL)** — `fee_cap_lamports` in `config.json`, 5× below the
listing's ≈ 0.05 SOL ceiling, which is a ceiling and not a target: the
cap is cumulative, the spend ledger counts every attempted send (failed
transactions still pay fees), and there is no override. Expected **net
burn ≈ 1,070,260–1,245,260 lamports (≈ 0.0011–0.0013 SOL)** — probe fees
plus setup fees; the sender floats (7 × 1,090,880 = 7,636,160 lamports)
leave the main account only as float and return via the end-of-campaign
sweep. Total fees actually spent: [FILL AFTER RUN: total lamports from
`data/spend_ledger.jsonl`, and the same figure in SOL].

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
across blocks.

### 3.5 Safety design (engineering)

- **Dry-run by default.** `send` without `--live` builds and signs all 11
  probe transactions per target with ephemeral keys and broadcasts
  nothing; the shipped one-command demo (`docker compose run --rm probe
  dry-run`) needs no keys at all.
- **Live mode is gated four ways**: the explicit `--live` flag; a keypair
  file supplied only through the `PROBE_KEYPAIR_FILE` environment
  variable; a fee cap present in the config (if the cap key is missing,
  live mode refuses to start); and a minimum main-wallet balance
  (9,000,000 lamports).
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
  one-blockhash-per-path behaviour.

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

**Raw data shipped in this repo** (force-added at publication;
`.gitignore` excludes data files by default):

- `data/send_log.jsonl` — one record per attempted send: signature,
  target label, window start slot, set, `send_seq`, price
  (µL-per-CU), fee paid, local timestamp, status.
- `data/spend_ledger.jsonl` — every fee-bearing attempt, the input to the
  spend-cap accounting of §3.3.
- `data/analysis_*.json` — the analyzer's full output: `generated`
  timestamp; `summary` (per-target statistics, §6); and `records` — every
  probe with its recovered **slot** and **index within the block**.

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
`data/analysis_*.json` → `summary[]`, one entry per target): measurement
date ← the entry's probe timestamps in `records` (cross-check
`send_log.jsonl.ts`); client (live-verified) ← the entry's `client`;
windows ← distinct `window_start` values per target in `records`; probes
landed/sent ← `probes_landed_in_window` / `probes_sent`; fee ρ ←
`fee_set.spearman_price_vs_position`; arrival ρ ←
`arrival_set.spearman_sendorder_vs_position`; conflict pairs ←
`conflict_pairs` (each entry's `first_landed`); Kendall's τ for the fee
ladder ← `fee_set.kendall_price_vs_position`.

## 6. Results

### 6.1 Per-validator ordering rule

| Date | Validator (operator) | Client (live-verified) | Windows | Probes landed in-window / sent | Fee rule — ρ price vs position (`fee_set`) | Arrival rule — ρ send-order vs position (`arrival_set`) | Conflict pairs — fee won / total (`conflict_pairs`) | Conclusion |
|---|---|---|---|---|---|---|---|---|---|
| [FILL AFTER RUN: measurement date (UTC) for this target's windows, from analysis `records[].ts`] | Kiln1 | [FILL AFTER RUN: `summary[].client` for kiln1] | [FILL AFTER RUN: distinct `window_start` count] | [FILL AFTER RUN: `probes_landed_in_window`] / [FILL AFTER RUN: `probes_sent`] | [FILL AFTER RUN: `fee_set.spearman_price_vs_position`; also report `fee_set.kendall_price_vs_position`] | [FILL AFTER RUN: `arrival_set.spearman_sendorder_vs_position`] | [FILL AFTER RUN: count of `conflict_pairs` with `first_landed` = high-fee member] / [FILL AFTER RUN: total conflict pairs] | [FILL AFTER RUN: H1 / H2 / H0 per §7 decision rules] |
| [FILL AFTER RUN: as above] | P2P.org | [FILL AFTER RUN: `summary[].client` for p2p_org] | [FILL AFTER RUN] | [FILL AFTER RUN] / [FILL AFTER RUN] | [FILL AFTER RUN] | [FILL AFTER RUN] | [FILL AFTER RUN] / [FILL AFTER RUN] | [FILL AFTER RUN] |
| [FILL AFTER RUN: as above] | Everstake | [FILL AFTER RUN: `summary[].client` for everstake_fd] | [FILL AFTER RUN] | [FILL AFTER RUN] / [FILL AFTER RUN] | [FILL AFTER RUN] | [FILL AFTER RUN] | [FILL AFTER RUN] / [FILL AFTER RUN] | [FILL AFTER RUN] |
| [FILL AFTER RUN: as above] | Galaxy | [FILL AFTER RUN: `summary[].client` for galaxy_fd] | [FILL AFTER RUN] | [FILL AFTER RUN] / [FILL AFTER RUN] | [FILL AFTER RUN] | [FILL AFTER RUN] | [FILL AFTER RUN] / [FILL AFTER RUN] | [FILL AFTER RUN] |
| [FILL AFTER RUN: as above] | Figment | [FILL AFTER RUN: `summary[].client` for figment_harmonic] | [FILL AFTER RUN] | [FILL AFTER RUN] / [FILL AFTER RUN] | [FILL AFTER RUN] | [FILL AFTER RUN] | [FILL AFTER RUN] / [FILL AFTER RUN] | [FILL AFTER RUN] |
| [FILL AFTER RUN: as above] | Coinbase 04 | [FILL AFTER RUN: `summary[].client` for coinbase04_harmonic] | [FILL AFTER RUN] | [FILL AFTER RUN] / [FILL AFTER RUN] | [FILL AFTER RUN] | [FILL AFTER RUN] | [FILL AFTER RUN] / [FILL AFTER RUN] | [FILL AFTER RUN] |

Per-window detail (the sign-consistency evidence behind each conclusion)
is in `data/analysis_*.json` under `fee_set.per_window[]` and
`arrival_set.per_window[]` (each entry: `window_start`, `n`, `spearman`).
Probes that landed outside their target's window and probes that never
landed are counted per target in the analysis output
(`probes_landed_outside_window`, `probes_never_landed`) and discussed in
§8 and §9.2 with their signatures.

### 6.2 Pooled per client family

| Client family | Fee ρ (n=24) | Arrival ρ (n=24) | Conflict fee-wins (n=6) | Reading |
|---|---|---|---|---|
| JitoLabs (Jito-Solana) | [FILL AFTER RUN: Spearman price-vs-position pooled over both JitoLabs targets' landed fee-ladder records (window-relative ranks pool across windows by design), from `data/analysis_*.json`] | [FILL AFTER RUN: pooled send-order ρ, same construction] | [FILL AFTER RUN: fee-wins summed over both targets' `conflict_pairs`] / 6 | [FILL AFTER RUN: family-level reading per §7] |
| Firedancer | [FILL AFTER RUN: as above, everstake_fd + galaxy_fd] | [FILL AFTER RUN] | [FILL AFTER RUN] / 6 | [FILL AFTER RUN] |
| HarmonicAgave | [FILL AFTER RUN: as above, figment_harmonic + coinbase04_harmonic] | [FILL AFTER RUN] | [FILL AFTER RUN] / 6 | [FILL AFTER RUN] |

Sample sizes are fixed by the design (§3): per validator, fee ladder
n=12, arrival ladder n=12, conflict pairs n=3; pooled per family, fee
n=24, arrival n=24, conflict pairs n=6. If any probe failed to land
in-window, the effective n for its set is the landed count in the
analysis output, and the table's reading must use that n — [FILL AFTER
RUN: state any reduced n here, with the affected target and set].

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
  this scale.
- **The path control** bounds the road-vs-scheduler confound: if the
  path-control probe's landed rank (via the alternate RPC) deviates
  systematically from what its price predicts in the main-path ladders,
  the affected window's reading is downgraded and the deviation is
  reported in §8 — [FILL AFTER RUN: state the path-control outcome per
  target from `data/analysis_*.json` records, or that no systematic
  deviation was observed].
- **Null results.** Where neither rule meets its bar, the conclusion is
  H0 — "no stable rule detectable at this probe scale" — stated as a
  conclusion with the raw data attached, per the listing's analysis
  criteria. No conclusion in §6 may claim more than §8's limitations
  allow: in particular, no fee *threshold* finer than the ladder spacing,
  and no load-dependence claim.

## 8. Findings

[FILL AFTER RUN: one subsection per client family, then a cross-family
synthesis. Each subsection must state, in this order: (1) the conclusion
(H1/H2/H0 per validator, from §6.1); (2) the numbers it rests on (fee ρ,
arrival ρ, per-window signs, conflict fee-wins, landed/sent counts — all
from `data/analysis_*.json` summary); (3) the strictness of the rule —
e.g. whether the fee effect held in every window or only on average, and
the jitter visible in the arrival ladder; (4) the path-control outcome
for the family's targets; (5) anything about the family's blocks that
qualifies the reading (missed windows, out-of-window landings,
never-landed probes — signatures in §9.2). The synthesis compares the
three families against the documented rules of §4 and states plainly
where production behaviour matched the documentation, where it diverged,
and where the honest answer is noise.]

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

### 9.2 Live-run incidents

[FILL AFTER RUN: dated entries for everything that deviated from
`DESIGN.md` during the live campaign — missed or skipped windows (with
target and window_start), probes that landed outside their window or
never landed (signatures, from the analysis output's
`probes_landed_outside_window` / `probes_never_landed`), any
client-attribution change or alternate substitution, RPC failures, and
any retry or re-run and its reason. If the campaign was uneventful,
write exactly that, with the campaign dates. This subsection may not be
left blank by omission.]

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

## 12. Conclusion

[FILL AFTER RUN: three short paragraphs. (1) The per-family verdicts from
§6.2/§8, stated at exactly the strength §7's rules and §11's limitations
allow — including H0 wherever it is the honest answer. (2) What this
means against the documented rules of §4: where production matched the
documentation, where it diverged, and what remains noise. (3) The
deliverable restated: a reproducible ruler — code, raw signatures and
slots, and pre-registered decision rules — that anyone can apply to the
next validator, the next client release, and the next upgrade.]
