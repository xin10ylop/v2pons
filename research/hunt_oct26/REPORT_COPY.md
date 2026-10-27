# Copy-trade hunt — can we ride a profitable sniper into these pools?

**Question (Oct 26–27).** Of the wallets that trade the pump-and-pull pools on Robinhood and Base,
is there one that is *consistently* profitable over the last ~5 days and that we could **copy** — land its
slot or the next block (+1) and engineer our own exit?

**Short answer: no wallet is both consistently profitable at real size and copyable.** The one "trader"
that clears tens of ETH is the trap line's own machinery, and every outside wallet that bought it was
rugged within seconds. The only seat that is both consistently green and survives a copy is the **dust
seat** — a sub-0.0001 ETH buy under a volume bot's tolerance — which pays on paper ~0.2–0.4 ETH over six
days at a 0.00009 stake, with a hard size ceiling and a real chance the seat closes. Base has one small,
real crowd-launch sniper (+0.26 ETH/6d) that is the only place a real-size copy sometimes got out alive.

All figures are from the tapes in `out/` (every swap, with reserves, for the pulled pools) over
**Oct 21–26**, both chains. Simulation reprices our buy and sell against each pool's real reserve path;
it does **not** model the operator reacting to *our* buy — that is what the follower / tolerance evidence
is for, and it is decisive.

---

## How a candidate was judged

A wallet is worth copying only if all four hold:

1. **Consistent** — green on 4+ of the 6 days (not one lucky pool).
2. **Profitable at a stake we'd actually use** — not only at its own dust size.
3. **Copyable** — when an *outside* wallet buys in its pools, the line lets the buy through instead of
   pulling on it. This is the user's hard skip rule: *"the operator's own bots are the only buyers it lets
   through… any entry of ours triggers the rug and costs the whole stake."*
4. **Exitable** — there is a sell point before the pull that we can hit from the slot or +1.

Scripts (all read-only, public RPCs): `snipers.py` groups round trips per trader and flags the
consistent ones; `pnlfast.py` / `pnlall.py` rank **every** trader exhaustively (via the pool token's
Transfer logs / tx senders); `copysim.py` reprices a copy at several stakes, entries and exit rules;
`entries.py` pulls *every* entry a wallet made (sold or not) so the copy is scored on the losers too;
`followers.py` resolves what happened to real-size strangers in a trader's pools; `tolerance.py` measures
how large an outside buy a line tolerates before it pulls.

---

## Robinhood

### Candidate 1 — `0xe6b451f7…` : the biggest number, and a trap

The most profitable "trader" on the chain by far. Its own six-day take and the paper copy:

| | result |
|---|---|
| its own profit | **+61.8 ETH**, green **6/6 days**, 2,681 round trips on 536 tick-spacing-1 pools |
| group | FLEET-LIKE — **488 wallets** behind one router, ~1 pool each (the line's own machinery) |
| copy 0.05, slot, mirror | **+33.7 ETH** (+25.1% a trip) on paper |
| copy 0.01, slot, mirror | +7.4 ETH on paper |

The paper number is a mirage. What happens to an **outside** wallet that buys these pools
(`followers.py`, 120 pools sampled):

- **15 of 15** real-size stranger buys **never got out** — net −0.068 ETH on 0.068 staked, **0 profitable**.
- The pull came a median **8 s** after the stranger's buy (pool life is 424 s — the pull is a reaction to
  the buy, not the clock).
- The one stranger that landed in the **copy position** (≤2 blocks after this router's buy) was rugged 20 s
  later. 1 for 1.

Tolerance of the tick-1 line by buy size (`tolerance.py`, 138 stranger buys): every size band is pulled
on within a few seconds and essentially nobody gets out. This is exactly the setup the user said to skip.
**Uncopyable.** The +61.8 ETH is the line paying its own wallets; an outside copy is the rug.

**Why not just exit 2–3 s after the buy?** (asked Oct 27; `exit_fast_e6b451f7.out`.) Two separate
problems, no shared fix. Of the 43 real-size (≥0.001) outside buys on this line:

| pull after the buy | share |
|---|---|
| within 0.5 s | 16% |
| within 1 s | **30%** |
| within 3 s | 30% (no new pulls between 1 and 5 s) |
| within 8 s | 51% |

The "median 8 s" is bimodal: the operator either pulls **inside 5–10 blocks** of the buy (30% of entries,
−100% at any exit speed — even a 0.5 s sell still eats 12 of the 43) or not for a while. And the 70% not
pulled instantly have **no bid yet at 3 s**: the fleet's profit comes from holding ~26 s and selling into
its own next machine buy; before that there is only fee + slippage (the no-reaction paper sim is already
red at hold-3: −0.6% a trip, 907 won / 1,774 lost). Replaying those 43 buys as a 0.05 ETH copy on the
recorded reserve path: **−31% a trip at every exit from 0.5 s to 3 s** (−0.66 ETH), −37% at 5 s, −52% at
8 s. The window where the trade pays (30–60 s) is exactly where the pull lands.

### Candidate 2 — `0x7ae81404…` (+ twin `0x68936d46…`) : the D65 dust seat — the one copyable, consistent seat

The known D65 crew's dust wallet, still trading as of **today 00:08 UTC** (nonce 48,302). It rides the
**volume-bot line** (v4, fee 10000, ts 200, 3 / 5 ETH pools) with a ~0.00002 ETH buy and gets out ~225 s
later, long before the pull.

| | result |
|---|---|
| its own profit (round trips) | **+0.093 ETH**, green **6/6 days**, 2,105 trips, **2,104 of 2,105 won** |
| its own profit (all entries, incl. never-sold) | **+0.069 ETH** — 3,618 entries, 1,513 never sold |
| stake | 0.00002 ETH · in at **0.4 s** · holds 225 s · exits a median 307 s before the pull |

This is the **only** Robinhood wallet (of **13,182** ranked exhaustively by `pnlfast.py`) that is green on
4+ days at ≥0.01 ETH besides `0x57ee6646` below. It clears the consistency bar cleanly.

**Copy, scored on all 3,618 entries including the 1,513 it never sold** (`copysim.py` + `entries.py`,
entry +1, over six days):

| stake | mirror its exit | cap 180 s | cap 120 s |
|---|---|---|---|
| 0.00002 | +0.071 | +0.057 | +0.031 |
| 0.00005 | +0.210 | +0.175 | +0.111 |
| 0.00009 | **+0.395** | +0.332 | +0.217 |

Mirror (sell the block it sells) is best because it never holds into a pull. Engineering the exit around
its sell helps a little more — selling ~30–120 s *after* its sell lifts the six-day total to **+0.41 to
+0.48 ETH** at 0.00009 (pull-outs stay rare because these pools live ~430 s and it exits ~300 s early); a
20% trailing stop capped at 120 s gives +0.46. A hindsight best-block exit caps the upside at +0.86 — so
~0.4–0.5 ETH is roughly half of the theoretical ceiling. Slot and +1 are within 0.0001 ETH of each other
(we don't need its exact block).

**The catches, both real:**

- **Size ceiling.** The line tolerates dust and pulls on anything bigger. By stranger buy size
  (`tolerance.py`, 336 buys): a buy of **0.0001–0.0002 ETH is pulled within 5 s 97% of the time** (base
  rate 1%), **0.0002–0.001 → 96–100%**, and 0% of these got out. Even **sub-0.0001 ETH** strangers that
  bought after the first few seconds mostly did **not** get out (0% in the 0.00006–0.0001 band). D65
  survives because it is dust *and* first (0.4 s). A copy must stay **≤~0.00009 ETH and land in the first
  seconds**, or it trips the rug and loses the stake. So the per-wallet ceiling is ~0.00009 ETH, and the
  +0.4 ETH/6d is a ceiling on *this seat*, not something that scales with stake.
- **We'd be adding to the size.** Copying means our buy lands right next to D65's in the same pool — the
  line sees the *combined* size. Two twin dust wallets already sit there; a third buyer nudges the pool
  toward the threshold that triggers the pull. Landing *ahead* of D65 means being the thing D65 is fast
  to beat.
- **Seat risk.** ~0.07–0.09 ETH/6d (~0.012–0.015 ETH/day) is real but small, and it ends the day the line
  changes its tolerance or a competitor crowds the seat.

Verdict: **the only Robinhood seat that passes all four tests**, but it is a dust seat with a hard ceiling
around 0.00009 ETH/trade and a plausible path to closing. Worth a small live test, not size.

> **Superseded by the deep dive (Oct 27, `REPORT_SEAT.md`):** the seat is an allowlist. 520 buys by other
> bots landed in the residents' slot over the six days and 477 (92%) were pulled within 5 s; the residents'
> twin was accepted on day one with zero history. With an engineered exit (tripwires on any stranger buy or
> new wallet, take-profit 6.5–7.5×) the seat would be worth ~+0.70 ETH/6d at 0.00009 — but a new wallet
> does not get it. **No live test recommended.**

### Candidate 3 — `0x57ee6646…` : smaller D65-style dust on the tick-1 line

Second (and last) exhaustive survivor: +0.024 ETH over six days, green 6/6, 0.00006 ETH buys on the
tick-1 line, in at 13 s. Same shape as D65 but smaller and slower, and it rides the *trap* line — thinner
margin, closer to the rug. Lower priority than D65.

### The D65 router `0x65050a9b…`

Its round trips look green (+2.24 ETH/6d) but it is **not consistent** — +1.95 of that is one day
(Oct 21), −/flat the rest — and its pools rug outside wallets hard (48 of 81 strangers never sold,
−17 ETH net). Not a copy target.

---

## Base

### `0xd8ba9d1a…` : a small, real crowd-launch sniper — the one real-size copy that sometimes survives

Spins up a fresh wallet per trip through its router and snipes genuine crowd launches (pools that live
~20 min and draw dozens of real buyers), not a pure rug line.

| | result |
|---|---|
| its own profit | **+0.65 ETH**, green **4/4 active days**, 16 trips on 6 pools |
| copy 0.04, slot, mirror | **+0.26 ETH** (+41% a trip), 11/16 won |
| copy 0.04, +1, mirror | +0.18 ETH |
| copy 0.04, slot, cap 120 s | +0.25 ETH |

Crucially, in its pools **strangers sometimes get out**: of 11 real-size buys in the copy position,
**6 got out (4 with a profit)**, net −0.32 on 0.58 staked. That is the only line in this whole hunt where
a real-size copy wasn't an automatic loss — because it's sniping real launches, not operating a rug.

**Catch:** small and noisy. Only 4 active days, 6 pools, 16 trips; Base round trips collapsed Oct 25–26.
Low, lumpy volume means low confidence and real variance (5 of 16 copies lost). A candidate for a small,
watched live test, not a standing strategy.

### Base dust bots

`pnlall.py` ranked every Base trader exhaustively: only `0x02641039` is consistent (+0.049 ETH), on the
1.2 ETH fee-0 line that **stopped Oct 24**. Top earners otherwise are one-offs (`0x7926f001` +0.337 in a
single pool). Nothing standing to copy.

---

## Bottom line

| candidate | chain | consistent? | profit at real size | copyable (survives our buy)? | verdict |
|---|---|---|---|---|---|
| `0xe6b451f7` tick-1 line | RH | 6/6, +61.8 ETH | huge **on paper** | **No** — 15/15 strangers rugged in ~8 s | skip (trap line's own bots) |
| **`0x7ae81404` D65 dust** | RH | **6/6, +0.07–0.09 ETH** | only as **dust ≤~0.00009** | **Yes, dust only** | **small live test** |
| `0x57ee6646` dust | RH | 6/6, +0.024 ETH | dust only, on the trap line | marginal | low priority |
| **`0xd8ba9d1a` launch sniper** | Base | 4/4, +0.65 ETH | +0.26 ETH/6d copy at 0.04 | **partly** — 6/11 strangers got out | **small watched test** |
| everything else | both | no | — | — | skip |

- **No wallet clears tens of ETH that we can copy.** The big number is the trap line paying itself; an
  outside buy there is the rug, every time.
- **The only consistent, copyable Robinhood profit is the dust seat** under the volume bot's ~0.0001 ETH
  tolerance: ~0.4–0.5 ETH over six days at a 0.00009 stake with a mirror-plus exit, hard-capped by size,
  and at risk of closing — and copying adds our size next to D65's, nudging the pull threshold.
- **Base's `0xd8ba9d1a` is the one real-size copy that sometimes survives,** because it snipes real
  launches rather than a rug line; but it's small and lumpy.

Per the standing rule, this is read-only analysis. Point an engine at either seat only on the owner's
word, and only after a live exit test at dust size confirms the copy gets out before the pull.

### Files
Scripts: `tape.py`, `snipers.py`, `copysim.py`, `entries.py`, `followers.py`, `tolerance.py`,
`pnlfast.py`, `pnlall.py`. Saved runs: `snipers_rh.out` / `snipers_base.out`, `pnlfast_rh.out`,
`pnlall_base.out`, `copysim_rh_e6b451f7.out`, `copysim_rh_7ae81404_trips.out` /
`copysim_rh_7ae81404_entries.out`, `copysim_rh_65050a9b.out`, `copysim_base_d8ba9d1a.out`,
`followers_rh_e6b451f7.out` / `followers_rh_7ae81404.out` / `followers_rh_65050a9b.out` /
`followers_base_d8ba9d1a.out`, `tolerance_rh_volume.out` / `tolerance_rh_tick1.out`. Tapes are in `out/`
(gitignored).
