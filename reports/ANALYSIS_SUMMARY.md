# Analysis summary — "Inside the Block" probe (final dataset, runs 1–3)

Generated **2026-10-31** from the complete measurement campaign: three live
runs on Solana mainnet against six target validators. Every number below
traces to a named artifact; nothing is estimated or rounded into existence.

**Artifacts**

- Canonical analyzer output (all runs pooled):
  `data/analysis_20261031T014525Z.json` (`probe analyze`, generated
  2026-10-31T01:45:25Z; earlier per-run outputs:
  `data/analysis_20261031T010526Z.json`,
  `data/analysis_20261031T012938Z.json`).
- Send log / spend ledger: `data/send_log.jsonl`, `data/spend_ledger.jsonl`.
- Run consoles: `data/live_run_console_20261031T005609Z.log` (run 1),
  `data/live_run2_console_20261031T011307Z.log` (run 2),
  `data/live_run3_console_20261031T013457Z.log` (run 3).
- Run-time gossip checks: run 1 — the `schedule` check quoted in
  `reports/READINESS.md` (~2026-10-31T00:55Z); run 2 —
  `data/schedule_check_20261031T011033Z.log`; run 3 —
  `data/schedule_check_20261031T013442Z.log`. All three agree.

**Method note.** Landing counts and per-validator statistics are the
analyzer's own output (`probe/analyzer.py`: landed position = (slot, index
in block); only landings inside the target window feed the ordering
statistics; "never landed" means not found in the searched span — the
window plus the 8 following slots). Per-run splits and the per-client
pooling were produced by running the analyzer's own `summarize()` function,
unmodified, on the annotated records of the canonical analysis file,
split by send timestamp (run boundaries are separated by wide idle gaps)
and, for the client pooling, relabelled with the run-time gossip client
attribution below. Landed-slot offsets are computed from the same records'
`landed_slot` fields.

**Run-time client attribution** (gossip `clientId` + version, identical at
all three run-time checks; gossip clientId is self-reported):

| target | validators.json snapshot | run-time (all 3 runs) |
|---|---|---|
| kiln1 | JitoLabs 4.3.2 | JitoLabs 4.3.2 |
| p2p_org | JitoLabs 4.3.2 | JitoLabs 4.3.2 |
| everstake_fd | Firedancer 26.10.4 | **JitoLabs 4.3.2** |
| galaxy_fd | Firedancer 26.10.4 | Firedancer 26.10.5 |
| figment_harmonic | HarmonicAgave 4.3.2 | HarmonicAgave 4.4.0 |
| coinbase04_harmonic | HarmonicAgave 4.3.2 | HarmonicAgave 4.3.2 |

Per-client pooling therefore groups: **JitoLabs** = kiln1 + p2p_org +
everstake_fd; **Firedancer** = galaxy_fd; **HarmonicAgave** =
figment_harmonic + coinbase04_harmonic. (The analyzer's own output groups
by the validators.json snapshot labels; where the two differ — everstake_fd
— the per-validator table below is unaffected, only the pooling changes.)

## 1. Landing counts

Windows: each run planned 18 (6 validators × 3). Run 1 executed 16
(2 skipped by the never-fire-late rule); run 2 attempted 16 (12 broadcast
fully, 4 lost all 11 probes to blockhash expiry — §5b — and 2 skipped);
run 3 executed 14 (4 skipped).

### Per run

| run | sent | in-window | outside-window | never landed | in-window share |
|---|---|---|---|---|---|
| 1 (2026-10-31T00:56Z) | 176 | 10 | 123 | 43 | 5.7% |
| 2 (2026-10-31T01:13Z) | 132 | 22 | 86 | 24 | 16.7% |
| 3 (2026-10-31T01:35Z) | 154 | 10 | 99 | 45 | 6.5% |
| **combined** | **462** | **42** | **308** | **112** | **9.1%** |

Run 2 attempted a further 44 probes that were never broadcast (§5b); they
are in no landing count. Run 3 broadcast 154/154 attempts with zero send
errors.

### Per validator, combined (sent / in / out / never)

| validator (run-time client) | sent | in | out | never |
|---|---|---|---|---|
| everstake_fd (JitoLabs) | 99 | 12 | 58 | 29 |
| figment_harmonic (HarmonicAgave) | 99 | 8 | 70 | 21 |
| galaxy_fd (Firedancer) | 77 | 11 | 56 | 10 |
| kiln1 (JitoLabs) | 66 | 5 | 48 | 13 |
| coinbase04_harmonic (HarmonicAgave) | 66 | 4 | 43 | 19 |
| p2p_org (JitoLabs) | 55 | 2 | 33 | 20 |

### Per validator per run (sent / in / out / never)

| validator | run 1 | run 2 | run 3 |
|---|---|---|---|
| coinbase04_harmonic | 22 / 0 / 14 / 8 | 11 / 1 / 10 / 0 | 33 / 3 / 19 / 11 |
| everstake_fd | 33 / 4 / 20 / 9 | 33 / 3 / 11 / 19 | 33 / 5 / 27 / 1 |
| figment_harmonic | 33 / 1 / 23 / 9 | 33 / 5 / 23 / 5 | 33 / 2 / 24 / 7 |
| galaxy_fd | 22 / 1 / 16 / 5 | 33 / 10 / 23 / 0 | 22 / 0 / 17 / 5 |
| kiln1 | 33 / 2 / 27 / 4 | 22 / 3 / 19 / 0 | 11 / 0 / 2 / 9 |
| p2p_org | 33 / 2 / 23 / 8 | 0 / 0 / 0 / 0 | 22 / 0 / 10 / 12 |

(p2p_org broadcast nothing in run 2: one window skipped, two lost to
blockhash expiry.)

## 2. Fee-ladder statistics (in-window landings only)

Convention (analyzer): Spearman ρ of price vs landed position — strongly
**negative** would mean fee-following (higher price lands earlier);
ρ of send order vs landed position strongly **positive** means arrival
order preserved. Note the design collinearity: the ladder is sent
cheapest-first, so price order and send order are identical within the
fee set and the two ρ's are necessarily equal; the discriminating outcome
would have been a negative ρ (landed order reversed against both). All 42
in-window landings in the entire dataset are fee-set probes (§5d), so this
is the only set with any in-window evidence at all.

### Per validator, combined

| validator | n | ρ price | ρ send-order | Kendall τ-b price | per-window ρ (window: n, ρ) |
|---|---|---|---|---|---|
| everstake_fd | 12 | +1.0 | +1.0 | +1.0 | 463494996: 2, +1.0 · 463495156: 2, +1.0 · 463500068: 2, +1.0 · 463505652: 3, +1.0 |
| galaxy_fd | 11 | +1.0 | +1.0 | +1.0 | 463499512: 4, +1.0 · 463499648: 3, +1.0 · 463499756: 3, +1.0 |
| figment_harmonic | 8 | +1.0 | +1.0 | +1.0 | 463499484: 3, +1.0 · 463500012: 2, +1.0 · 463505872: 2, +1.0 |
| kiln1 | 5 | +1.0 | +1.0 | +1.0 | 463500964: 3, +1.0 |
| coinbase04_harmonic | 4 | +1.0 | +1.0 | +1.0 | 463505604: 2, +1.0 |
| p2p_org | 2 | 0.0 | 0.0 | 0.0 | none (no window with ≥2 in-window fee probes; the 2 probes pooled across two windows tie in landed rank) |

**Sign consistency**: 12 windows across the dataset have a computable
per-window fee ρ (n ≥ 2); all 12 are +1.0 — sign-consistent in 12/12
occasions. The honest caveat is the sample grain: per-window n is only
2–4, where Spearman can take only coarse values (at n = 2 it is ±1 by
construction). The pooled result says: in-window, landed order matched
send order exactly in every observed case; **no fee-following reversal
was observed at any of the four price points (0 / 10k / 50k / 250k
µL-per-CU) in this sample**. That is evidence about these windows, not a
characterisation of any scheduler.

### Per client (run-time attribution), combined

| client | validators pooled | sent / in | fee n | ρ price | ρ send-order | Kendall | windows with ρ (all +1.0) |
|---|---|---|---|---|---|---|---|
| JitoLabs | kiln1, p2p_org, everstake_fd | 220 / 19 | 19 | +1.0 | +1.0 | +1.0 | 5 (n = 2,2,2,3,3) |
| HarmonicAgave | figment_harmonic, coinbase04_harmonic | 165 / 12 | 12 | +1.0 | +1.0 | +1.0 | 4 (n = 3,2,2,2) |
| Firedancer | galaxy_fd | 77 / 11 | 11 | +1.0 | +1.0 | +1.0 | 3 (n = 4,3,3) |

### Per run (fee set, validators with a computable pooled ρ)

- Run 1: everstake_fd n = 4, ρ = +1.0 (windows 463494996, 463495156, both
  +1.0); kiln1 n = 2, ρ = 0.0 and p2p_org n = 2, ρ = 0.0 (each pooled
  across two windows with one in-window fee probe each — per-window ρ
  not computable); figment_harmonic n = 1, galaxy_fd n = 1,
  coinbase04_harmonic n = 0 — **not computable**.
- Run 2: galaxy_fd n = 10, ρ = +1.0 (3 windows, all +1.0);
  figment_harmonic n = 5, ρ = +1.0 (2 windows, all +1.0); everstake_fd
  n = 3, ρ = +1.0 (1 window, n = 2); kiln1 n = 3, ρ = +1.0 (1 window,
  n = 3); coinbase04_harmonic n = 1 — **not computable**; p2p_org
  broadcast nothing.
- Run 3: everstake_fd n = 5, ρ = +1.0 (window 463505652: n = 3, +1.0);
  coinbase04_harmonic n = 3, ρ = +1.0 (window 463505604: n = 2, +1.0);
  figment_harmonic n = 2, ρ = +1.0 (window 463505872: n = 2, +1.0);
  galaxy_fd, kiln1, p2p_org n = 0 — **not computable** (no in-window
  landings).

## 3. Arrival-ladder statistics — not computable

Arrival set: 168 probes sent (4 per executed window), **0 landed
in-window in any run, for any validator or client** (133 landed outside
their window within the searched span, 35 not found in the span). With
zero in-window observations, the analyzer returns n = 0 and ρ = null
everywhere: the arrival-order statistic is **not computable** on this
dataset. This is a property of the submission path (§5), not evidence
that arrival order does or does not survive inside these schedulers.

## 4. Conflict pairs — not computable

Conflict set: 84 probes sent (42 pairs). No window in any run has both
pair members landed in-window (0 pairs), so the analyzer reports no
conflict outcomes — the fee-vs-arrival conflict statistic is **not
computable**. (Records-level observation, not an analyzer statistic:
both members landed somewhere in the wider searched span in 17 windows,
never both inside the target window.)

## 5. Engineering findings

### a. Run 1 — burst lateness (build-after-wait)

Run 1 fetched blockhashes after the window wait; the two public-RPC
round-trips pushed bursts late: 10/176 in-window (5.7%). All 10 in-window
landings sit at offset +3 from window start — the last slot of each
4-slot window; outside landings (n = 123) fell 1–8 slots after window
end, median 5 (≈2 s). Fix (before run 2): build + sign before the wait.

### b. Run 2 — blockhash expiry (the build-first trade-off)

With bursts built before the wait, later-queued windows whose turn came
> ~150 slots after their build reached the burst with an expired
blockhash: **all 44 probes in 4 windows** (p2p_org 463500264 and
463500740, kiln1 463501236, coinbase04_harmonic 463502600) failed
simulation with RPC −32002 after 4 tries each — 40 recorded as
`BlockhashNotFound`, 4 as `Blockhash not found`, the same failure in two
RPC message formats — and were **never broadcast; no fees were charged
on-chain for them**. Run 2 still improved in-window share to 22/132
(16.7%), with in-window offsets 1–3 (median 2) vs run 1's uniform +3.

**Fix (before run 3)**: `execute_window` records the chain slot at which
each path's blockhash was fetched, and at burst time re-fetches +
re-signs once for any path aged > 100 slots (safety margin under the
~150-slot validity); fresh paths fire exactly as built. Verified by the
unit suite (14/14, including the one-blockhash-per-path burst test) and
a scripted fresh/stale functional check (stale path re-signed, fresh
path byte-identical). **Run 3 result: 154/154 broadcast, zero send
errors, zero blockhash losses** — including the late-queued windows
(p2p_org 463506560, everstake_fd 463506672) that are the run-2 failure
shape. The failure did not recur.

### c. Path latency, quantified from landed-slot offsets

Combined dataset (offsets in slots; in-window offset measured from
window start, outside offset from window end):

- In-window landings (n = 42): offset +1…+3, median +3 — landings cluster
  at the **end** of the 4-slot windows; none at offset 0.
- Outside landings (n = 308): 1…17 slots after window end, median 5.
- By submission path — rpc_primary (10 of 11 probes per window;
  n = 292 outside): median 5, range 1…17. rpc_alt (the 1-per-window
  path-control probe via the second endpoint; 42 sent): **0 in-window
  landings**; 16 landed in the searched span, all outside, offsets
  **5…17 after window end, median 7** — systematically later than the
  primary path's outside landings; 26 not found in the span.
- Per run, outside-offset medians: run 1 = 5 (n = 123, max 8),
  run 2 = 4 (n = 86, max 17), run 3 = 5 (n = 99, max 8).

The two paths are two endpoints into the same public RPC infrastructure,
not two network routes to the leader (see READINESS "Honest limits");
the offset gap quantifies the endpoint difference for our probes, not a
scheduler property.

### d. Only the head of each burst ever landed in-window

All 42 in-window landings are fee-set probes — the first four sends of
each 11-probe burst. Arrival (0/168), conflict (0/84) and control (0/42)
probes never landed in-window in 462 sends. Combined with §5c (landings
cluster at window end / just after), the dataset's consistent picture is
that the burst, fired at window start − 2 slots via public RPC, mostly
reached leaders at or after the window's close; only its earliest sends
occasionally made the tail of the window.

## 6. Fees (spend ledger, attempt-time accounting)

The ledger records each probe's planned fee when the send is attempted,
so run 2's probe figure includes the 44 never-broadcast probes (their
fees were not charged on-chain). Cap: 10,000,000 lamports, unchanged
throughout.

| run | probe fees | funding fees | total | ledger entries |
|---|---|---|---|---|
| 1 | 889,120 | 160,000 | 1,049,120 | 208 |
| 2 | 889,120 | 125,000 | 1,014,120 | 201 |
| 3 | 777,980 | 145,000 | 922,980 | 183 |
| **cumulative** | | | **2,986,220** | |

Main-account balance: 12,000,000 lamports before run 1 → 3,496,600 after
run 1 → 2,617,611 after run 2 → **1,876,581 after run 3** (slot
463,506,723). The run-3 delta (−741,030) reconciles exactly: funding
transfers out 456,100 + funding fees 145,000 + main-paid probe fees
140,000 + probe dust sent 84 − dust received 154. Sender floats remain
deployed in the 7 sender accounts; the end-of-campaign sweep has not
been performed.

## 7. What this dataset supports

- With a public-RPC submission path and 4-slot leader windows, the
  probe bursts predominantly missed their target windows in all three
  runs (in-window 9.1% combined), despite two successive timing fixes
  that each removed the previous run's dominant failure mode (lateness,
  then blockhash expiry; run 3 had zero send-layer losses).
- Where in-window evidence exists at all (fee set only, pooled n = 42
  across 12 windows), landed order matched send order exactly
  (ρ = +1.0, sign-consistent 12/12 windows, per-window n = 2–4): **no
  fee-following ordering was observed in-window at the tested price
  points**, for any of the three run-time client families. Given the
  sample grain, the pre-registered reading is the weak one: no stable
  fee-ordering rule is detectable in this data — not proof that none
  exists inside these schedulers.
- Arrival-order and conflict-resolution rules are **not measured** by
  this dataset (zero in-window observations for both sets).
