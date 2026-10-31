# Inside the Block — measurement report

**Bounty:** Superteam Earn, "Inside the Block: How Solana Validators Order
Transactions" (Superteam Ukraine) · **Network:** Solana Mainnet ·
**Alpenglow side:** after (all measurements post-2026-10-21) ·
**Campaign dates:** _(empty — not yet run)_ ·
**Probe wallet (public):** CAtqKwVaYbZqB33sLNvsKNpr7Y8BnZf3X6V4PCjHrP2v ·
**Total fees spent:** _(empty)_ of 10,000,000-lamport code cap ·
**Raw data:** `data/send_log.jsonl`, `data/spend_ledger.jsonl`,
`data/analysis_*.json` (signatures + slots for every probe; verify with
`getBlock`).

## Method in one paragraph

For each target validator we fired 11 self-sent probe transactions into each
of 3 separate leader windows: a 4-rung fee ladder on account-disjoint pairs
(sent cheapest-first), a 4-transaction zero-fee arrival ladder, a crossed
conflict pair sharing one written account, and one path-control probe via an
alternate RPC. Landed positions were read back from the produced blocks; a
probe counts as evidence about a validator only if it landed inside that
validator's window. Statistics: Spearman/Kendall rank correlations of price
and send order against landed position, per validator and pooled per client.
Full design + budget arithmetic: `DESIGN.md`.

## Results — per-validator ordering rule

| Date | Validator (operator) | Client (live-verified) | Windows | Probes landed / sent | Fee rule (ρ price vs position) | Arrival rule (ρ send-order vs position) | Conflict pairs (fee won / total) | Conclusion |
|---|---|---|---|---|---|---|---|---|
| _(empty)_ | Kiln1 | JitoLabs | | / | | | / | |
| _(empty)_ | P2P.org | JitoLabs | | / | | | / | |
| _(empty)_ | Everstake | Firedancer | | / | | | / | |
| _(empty)_ | Galaxy | Firedancer | | / | | | / | |
| _(empty)_ | Figment | HarmonicAgave | | / | | | / | |
| _(empty)_ | Coinbase 04 | HarmonicAgave | | / | | | / | |

## Results — pooled per client

| Client | Fee ρ (n=24) | Arrival ρ (n=24) | Conflict fee-wins (n=6) | Reading |
|---|---|---|---|---|
| JitoLabs (Jito-Solana) | _(empty)_ | _(empty)_ | _(empty)_ | _(empty)_ |
| Firedancer | _(empty)_ | _(empty)_ | _(empty)_ | _(empty)_ |
| HarmonicAgave | _(empty)_ | _(empty)_ | _(empty)_ | _(empty)_ |

## What went wrong

_(To be completed after the campaign — missed windows, dropped probes,
client-attribution changes, RPC failures, and any deviations from DESIGN.md
are recorded here, dated, with the affected data identified. Nothing in this
section may be left blank by omission: an uneventful campaign is stated as
such.)_

## Limitations

- Gossip `clientId` is self-reported by each node; attributions are
  cross-checked against version strings and public registries, not proven.
- RPC-path vs scheduler separation is bounded by the path control, not
  eliminated (no raw-QUIC TPU submission).
- Fee thresholds cannot be localised finer than the ladder rungs
  (0 / 10k / 50k / 250k µL-per-CU).
- Null results ("no stable rule at this probe scale") are reported as
  conclusions, not failures.
