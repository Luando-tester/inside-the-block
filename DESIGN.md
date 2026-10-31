# Design — the leanest campaign that still answers the question

**Question (per validator):** when this validator leads, what rule decides which of
our transactions lands earlier — fee-per-compute-unit, arrival order, or no stable
rule at probe scale — and how strictly does the rule hold inside conflict chains?

**Budget stance.** The listing frames total measurement spend at ≈0.05 SOL with a
code-enforced cap. That figure is a *ceiling, not a target*. This design's net burn
is ≈**0.0011 SOL** — about 2% of the ceiling — because the dominant cost on Solana
is the fixed 5,000-lamport base fee per signature, and the experiment needs
hundreds of signatures, not thousands.

## Probe set — 11 transactions per leader window

All probes are dust transfers (1–11 lamports; the amount encodes the send
sequence so no two probes in a window are byte-identical under one
blockhash — identical transactions would share a signature and the second
could never land) between the project's own 8 accounts
(main + S1..S7), each topped up to the rent-exempt minimum (890,880 lamports)
plus a spend float before each validator's windows. The top-up is idempotent
(it sends only what is missing) and is sized per validator cycle: the heaviest
payer, S2, draws 15,010 lamports of fees per window — 45,030 per 3-window
cycle — against the 200,000-lamport float, so no account can run dry inside a
cycle. (A single campaign-wide top-up would NOT suffice: S2's 18-window draw
is 270,180 lamports.) Every account already exists, so a dust transfer is
a valid minimal transaction, and every lamport is recoverable by the final
sweep.

| Set | n | Construction | What it isolates |
|---|---|---|---|
| Fee ladder | 4 | Pairs (M→S1) (S2→S3) (S4→S5) (S6→S7) — pairwise account-disjoint. CU prices 0 / 10,000 / 50,000 / 250,000 µL-per-CU, sent cheapest first. | Fee-density rule. Fee-following ⇒ landed order ≈ reverse of send order; arrival-following ⇒ landed ≈ send order. |
| Arrival ladder | 4 | Same 4 disjoint pairs, all price 0, rapid burst (30 ms gaps), recorded send order. | Whether arrival order survives at all, and its jitter. |
| Conflict pair | 2 | (S2→S1) price 0 sent first; (S3→S1) at 250,000 µL/CU sent second. Both write S1 ⇒ must serialise. | The rule *inside* a conflict chain — the case users feel on contested accounts. |
| Path control | 1 | (S7→M) at 10,000 µL/CU, sent via the alternate public RPC endpoint. | Scheduler rule vs. road-to-the-scheduler (RPC forwarding path). |

One window targets one leader's slot run (normally 4 consecutive slots). Probes
are fired so they arrive inside the window; the read-back credits a probe to the
target **only if it landed inside the window's slots** — a probe landing in the
next leader's block is recorded as missed, never as evidence about the target.

## Repetition

3 windows per validator × 6 validators = **18 windows, 198 probe transactions**.
Windows for a validator are taken on separate occasions (different leader
rotations, spread across the campaign days), never three back-to-back rotations
of the same leader, so a single machine state cannot masquerade as a rule.
Planning enforces a minimum lead (`min_window_lead_slots` in config, default
75 slots ≈ 30 s). Leader runs are cut into rotation-sized (≤4-slot) windows
aligned to the run start, and a window is returned only whole — never as the
tail of a run that has already started.

## Arithmetic (all of it)

Per transaction, CU limit = 1,000 (a transfer + two Compute Budget instructions
needs ~300; the limit sets the priority-fee basis, so it is kept small and fixed):

- base fee: 5,000 lamports (1 signature)
- priority fee: price × 1,000 µL = 0 / 10 / 50 / 250 lamports for the ladder prices

Per window:

| Set | Fees (lamports) |
|---|---|
| Fee ladder | (5000+0) + (5000+10) + (5000+50) + (5000+250) = **20,310** |
| Arrival ladder | 4 × 5,000 = **20,000** |
| Conflict pair | (5000+0) + (5000+250) = **10,250** |
| Path control | 5000+10 = **5,010** |
| **Window total** | **55,570** |

Campaign: 18 × 55,570 = **1,000,260 lamports ≈ 0.00100 SOL**.
Setup/teardown: initial 7 funding transfers + 7 sweep transfers = 14 × 5,000
= 70,000, plus per-cycle top-up refreshes (at most 7 transfers before each of
the 5 later validators = ≤175,000).
**Net burn ≈ 1,070,260–1,245,260 lamports ≈ 0.0011–0.0013 SOL.**

Funding float (not burn): each sender is topped to 890,880 + 200,000 =
1,090,880 lamports; × 7 senders = 7,636,160 lamports leave the main wallet
over the campaign and ≈6.8M of it returns via the final sweep (the rest is
the senders' share of probe fees, already counted above). **Funding target
for the probe wallet: 0.009 SOL**, covering the float, main's own probe fees
(180,000 lamports over the campaign), funding-transfer fees, and retry
headroom. The code cap is set to **10,000,000 lamports (0.01 SOL)**
cumulative fees — 5× below the listing's ceiling — and the ledger counts
every attempt, including failed transactions (they still pay fees).

## What this sample can and cannot support

Per validator: fee ladder n=12 landed pairs (3 windows × 4), arrival ladder
n=12, conflict pairs n=3. Pooled per client (2 validators): fee n=24, arrival
n=24, conflict pairs n=6.

**Supportable:**
- Per-validator direction of Spearman's ρ between price and landed position,
  with cross-window sign consistency (3 windows agreeing in sign is the
  pre-registered bar for calling a rule "observed").
- Client-level pooled ρ (fee and arrival) over n=24 — enough to distinguish
  *strong* fee-following (ρ ≈ −0.8 or better) from *strong* arrival-following
  from *neither*, which is the bounty's core question.
- Conflict-pair tendency per client at n=6 pairs, stated with its binomial
  weight (6/6 fee-wins ⇒ p ≈ 0.016 under a fair-coin null; 5/6 ⇒ p ≈ 0.11,
  reported as suggestive only).

**Not supportable — and the report will not claim them:**
- A located fee *threshold* finer than the ladder spacing (4 rungs).
- Load-dependence of the rule (we do not measure block fullness as a factor).
- Sub-slot timing claims, or anything about validators outside the six targets.
- Bundle/Jito block-engine behaviour — out of scope by the listing's own terms.

**Pre-registered null:** "no stable rule detectable at this probe scale" is a
valid conclusion for any validator, per the listing's Analysis criteria, and
will be reported as such with the raw data attached rather than dressed up.

## Alpenglow boundary

Alpenglow activated on mainnet on 2026-10-21. All targets were selected after
the upgrade, all measurements will be taken after it, and none can be pooled
with pre-upgrade data (this project holds none). Client attributions are the
post-Alpenglow landscape: Frankendancer no longer exists on mainnet (unsupported
under Alpenglow), so the third client family alongside Jito-Solana and Agave
forks is the full Firedancer client (26.10.x).
