# Superteam submission package — "Inside the Block" (DRAFT, ready to submit)

> **Status (2026-10-31):** Report and all submission text below are FINAL.
> One step is outstanding: the public GitHub repo could not be created by
> the agent — GitHub's API returned `403 Resource not accessible by
> integration` for repository creation under the connected app. **Luân
> needs to do one 2-minute manual step** (see "Unblock step" below);
> after that the agent pushes the prepared snapshot (49 files) and the
> two URLs below become live exactly as written.
>
> **Deadline:** submit on Superteam Earn before **2026-11-05T21:59:59Z**
> (≈ 04:59 on 2026-11-06, Asia/Saigon). The listing is HUMAN_ONLY —
> submission must be made from Luân's own Superteam account; agent API
> submissions are rejected (403).

## Unblock step (Luân, ~2 minutes)

1. Open https://github.com/new — repository name: `inside-the-block`,
   visibility: **Public**, do **not** add a README/.gitignore/license
   (leave it completely empty). Create.
2. Open https://github.com/apps/meta-muse-ai/installations/new and make
   sure the Muse GitHub App installation includes the new
   `inside-the-block` repository (select it if asked).
3. Tell the agent "repo xong" — the agent pushes the prepared files and
   verifies the public repo + file tree, then confirms the URLs below
   are live.

## The links to submit

- **Repository (public):** https://github.com/Luando-tester/inside-the-block
- **Final report:** https://github.com/Luando-tester/inside-the-block/blob/main/reports/REPORT.md
- **Definitive statistics:** https://github.com/Luando-tester/inside-the-block/blob/main/reports/ANALYSIS_SUMMARY.md
- **Listing:** https://earn.superteam.fun/listing/inside-the-block-how-solana-validators-order-transactions/

## What to paste where (Superteam submission form)

**Project / repository link field** — paste:

```
https://github.com/Luando-tester/inside-the-block
```

**Description / submission text field** — paste the block below verbatim:

```
Inside the Block — how Solana validators order transactions: a reproducible mainnet measurement

We sent 462 controlled probe transactions into the leader windows of six production Solana validators spanning the three post-Alpenglow client families (JitoLabs, Firedancer, HarmonicAgave — attributed live from gossip at run time), read the landed order back from the produced blocks, and tested the pre-registered question: does ordering follow fee-per-compute-unit, arrival order, or no stable rule at probe scale?

Findings (2026-10-31, slots 463,494,708–463,506,672; full data, signatures and slots in the repo):
• 42 of 462 probes landed in-window. In every window where in-window fee order was observable (12 windows; pooled per client n = 19 / 11 / 12), landed order preserved send order exactly (Spearman ρ = +1.0). Fee-following — the negative ρ the documented fee-density rule predicts — was never observed at any of the four price points (0 / 10k / 50k / 250k µL-per-CU).
• The arrival-ladder question (0 in-window landings of 168) and the conflict-chain question (0 complete in-window pairs of 42) are unanswered by in-window data and are reported as not measured — not as negative results.
• The robust high-n result is about the submission path: with bursts fired through public RPC at 4-slot leader windows, 90.9% of probes missed their windows despite two successive, verified timing fixes; in-window landings cluster at window tails. Per the pre-registered decision rules, the verdict for all six validators is H0: no stable ordering rule detectable at this probe scale.

Engineering: dry-run by default, live only behind an explicit flag under a code-enforced 10,000,000-lamport spend cap (actual ledger total 2,986,220 lamports, an upper bound that includes 44 never-broadcast probes); one-command reproduction (docker compose run --rm probe dry-run); 14/14 unit tests; a complete dated "what went wrong" section covering burst lateness, blockhash expiry, skipped windows, a client-attribution change, and the dataset's selection effects and limitations.

Full report: https://github.com/Luando-tester/inside-the-block/blob/main/reports/REPORT.md
```

## Findings + limitations (one-paragraph version, if the form asks separately)

Three live passes on 2026-10-31 sent 462 probes at six validators;
42 landed in-window, all from the fee ladder (sent first in each burst —
a disclosed selection effect). Where fee order was observable it matched
send order exactly (ρ = +1.0, sign-consistent 12/12 windows, per-window
n = 2–4), so no fee-following was observed at the tested price points;
arrival-order and conflict-resolution rules were not measured (zero
in-window observations). Limitations: public-RPC submission path
(scheduler-vs-path separation bounded by a path control, not
eliminated), self-reported gossip client attribution, four fee rungs
only, all passes executed on one morning, per-window statistics coarse
at n = 2–4, and the Firedancer family resting on one validator at run
time. Every number is re-derivable from the shipped raw data with
`getBlock`.

## Checklist for Luân at submit time

- [ ] Repo created + app access granted (unblock step above) → agent
      pushes and confirms both URLs load publicly.
- [ ] Open the report URL once to confirm it renders.
- [ ] On the Superteam listing page, submit from your own account:
      repo link in the link field, the text block above in the
      description field.
- [ ] Submit before **2026-11-05T21:59:59Z**.
