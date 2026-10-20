# REPORT_T3: can we time the volume bot's first buy on the 3.0 line?

Hand-back about 00:40 UTC Oct 12. Two finders and up to two skeptics per rule. All work was read-only, on the public RPC only.
- "T" is the block of the bot's first buy in a 3.0 pool. "L" is the launch block.
- "d" counts blocks before T.
- Blocks are about 0.1 s. Our buy lands 1-2 blocks after the engine decides.

## Verdict

**No.** No event on chain or in the feed leads the bot's first buy by a stable 1-4 blocks. No schedule predicts T to within ±1
block. Ten candidate rules were tested, and none survived.

**The 3.0 line should not go live.** Keep it dry, but only as a free watch on the bot's offset. Its dry result ("38 of 38 priced
trades up") is not evidence. A dry buy never reaches the chain, so the operator never reacts to it. The same buy made live at L+13
was pulled 9 blocks later, and the bot never bought (-100%).

## The reaction, as measured

We looked at about 351 current-regime 3.0 pools, from 04:21 to 23:17 UTC Oct 11. Someone bought 0.00003 ETH or more before the
bot in 27 of them. The bot never bought in any of those 27, and every one was pulled. It bought in all 324 other pools.

| Bought before T | Pools | Pulled | Pull, blocks after that buy | Bot bought afterwards |
|---|---|---|---|---|
| 0x8c009ea5, 0.002 ETH at L+4..6 | 22 | 22 | 3 x6, 4 x6, 5 x3, 6 x3, 17 x2, 18, 23 | 0 |
| 0x7ae81404, 0.00297 ETH at L+1..2 | 4 | 4 | 5, 6, 7, 7 | 0 |
| our probe, 0.002 ETH at L+13 | 1 | 1 | 9 | 0 |
| **all** | **27** | **27** | **min 3, median 5, 22 of 27 within 7** | **0 of 27** |

- **After T.** Every non-dust stranger buy after T was pulled too, 5-27 blocks later (median 10-12 in each study). The bot never
  bought again in those pools.
- **Dust.** Buys under 0.00003 ETH draw nothing. The sentinel 0xe71a69f4 buys 2e-06 ETH at L+2..4 in every pool.
- **When the bot signs.** It signs its buy 1-4 blocks (0.1-0.4 s) before the buy lands. The buy's deadline is the signing second
  + 1,200 s. When T is the first block of its second, the deadline always points to the previous second. Nothing about the buy is
  visible before it is sequenced, and this chain has no public mempool.

**What a front earns, by where our buy lands** (integer v4 replay on the real swaps, sold right behind the bot's buy):

| Our buy lands | Result per trade |
|---|---|
| In block T ahead of the bot, or at T-1 | +5.8% to +6.6% mean, +6.0% to +7.4% median, worst +0.8% (n 48-200 per study) |
| T-2 or earlier | the pull comes 3+ blocks after our buy and the bot never buys: -100% |
| After the bot's buy | -2.4% (the fees) |

- To break even, 94% of fires must land in time.
- With today's feed, our sell usually lands at T+2 (REPORT_X). Against the fastest pull (3 blocks), that leaves only a buy landing in
  block T itself, ahead of the bot. Against the median pull (5 blocks), a buy landing in T-3..T is safe.
- One gap: no outside buy has ever landed in T-2..T. That the bot still buys in that case is an assumption (by then it has already
  signed).

## The bot's T

- T falls between L+18 and L+61, at p10/50/90 about 26/40/53. In seconds, T-L is 2-6 s and close to uniform.
- The best fixed ±1-block window holds 13-22% of pools in every slice studied.
- Before 04:22 UTC Oct 11, T was at L+8..10: 133 of 145 pools fell within ±1 block of L+9. The random delay started then.
- Nothing else we tested moves T:
  - the 10-minute launch clock, or the launch's place in it;
  - the sender's nonce, or which buyer wallet buys;
  - the previous pool's T (r -0.04), or how busy the bot is (r 0.02);
  - block number mod 2..60.

## The candidates

| # | Rule | Finder, held out | Skeptic 1 (unseen pools) | Skeptic 2 (unseen pools) | Front with the reaction | Status |
|---|---|---|---|---|---|---|
| 1 | Any tx to the bot router for another pool | in d 1-4 in 19% of pools, the background rate | 24 of 116 vs 21.6 expected (x1.11) | 12 of 49 vs 10.4 | -52% to -98% a trade at every arming point | refuted twice |
| 2 | Any tx from one of the bot's buyer wallets | 24%, background | 39 of 121 vs 36.9 (x1.06, P 0.37) | 18 of 48 vs 17.2 | -59% to -95% (-35% only with a 9-block pull) | refuted twice |
| 3 | Anything touching the pool, its token or T's buyer | 0 of 200 | 0 of 91 | 0 of 58 | never fires | no rule: confirmed null |
| 4 | A presigned or failed copy of the bot's buy | 0 of 200 | 0 of 180 (incl. Oct 4) | 0 of 49 | never fires | no rule: confirmed null |
| 5 | A 1444-byte launch (any line) just before T | 6% of pools | side check: 2 of 58 | side check: 1 of 48 | too rare to trade | not usable |
| 6 | The best data-mined tx type | no key repeats across sets | side check (91 pools): best key 7-12 hits against 28-79 early fires | the finder's top keys: -9% to +10% excess; "event in another line pool" went from +24.6% to 0% | -58% to -100% at every setting with 5+ trades | refuted |
| 7 | A fixed landing offset from L | best ±1 window 13-16% | side check: 15-19% | side check: 15% | -17% to -99% (20+ trades); the best cell was 2 trades at -2.5% | loses |
| 8 | Tail: nothing seen by L+54, so land at L+55 | 9 fires in 82 pools, 7 in time | not run | not run | -7.6% to -11% a fire; -18.7% over all 244 pools at L+53 | loses on its own held-out pools |
| 9 | Queue: the first bot action elsewhere after L+53 | 1 fire (training: 6 fires, -21.5%) | not run | not run | -21.5% (training) | loses |
| 10 | Pair: use the T of the pair's earlier launch | 3 fires, 1 in time | not run | not run | -45.9%; the pair's offsets are unrelated (r -0.12) | loses |

**Why rules 1, 2 and 6 fail.** They fire about once every 10-20 blocks in any case. Armed at launch, the first fire comes 6-43
blocks before T (median 26). So nearly every fire is an early buy, and an early buy is pulled at -100%.

**Rule 3: a new finding, but not a timing signal.** T's buyer is funded 30-74 blocks before T.
- 10-17 blocks before L, the pool's launcher calls the bot router: selector 7422a284, about 5.5 ETH, about 21 KB of calldata that
  carries the token's code.
- In 52 of 69 pools, that call lists the wallet that will make the first buy and sends it roughly the buy's size.
- So it tells us who will buy and about how much, but not when. Lead to T at p10/50/90 is 38/52/65 blocks, and the best ±1 window
  holds 8 of 52 pools, no better than the clock.
- After that call the buyer is not touched again. Watched live block by block, its balance and nonce did not change from T-15 to T-1
  in 21 of 21 pools.
- The launcher's approval of the bot router at L+3..5 (94 of 94 pools) is no better. T comes 20/33/48 blocks after it
  (p10/50/90).

**One near-break-even variant (not worth building).** Land blind at about L+53. If the bot has not bought, sell 2 blocks after our
buy, which is before the fastest pull.
- On 58 fresh pools: 8 trades, 3 in time, +1.1% a trade ($0.06).
- It needs our sell to land exactly 2 blocks after our buy, which our feed cannot promise.
- It would earn a few dollars a day.

## What would have to change on the operator's side

Any one of these would reopen the line:

1. **T goes back to a fixed offset from L**, as before 04:22 Oct 11, or as on 2.433 today (L+7..11). A front timed from L could then
   land at T-1 or T. Threshold: 80% or more of launches inside one 3-block window.
2. **The bot buys again after someone buys ahead of it, with the pull coming after its buy.** That was the 3.0 line before 04:22,
   and 2.433 until 15:31 Oct 11 (pull at T+3). Today this happened in 0 of 27 pools.
3. **A step visible 1-4 blocks before T.** For example, the buyer funded, approved or touched in the last few blocks, or the buy
   sent through a public mempool. Today the buyer is untouched for the last 15 blocks.

**The prize if it reopened.** An in-time front makes about +5.8% a trade. At 16-24 launches an hour, that is about $100-150 a day at
$5, or $330-470 a day at $15. This is an upper bound, before any misses.

## The cheapest watch (no new code, no stake)

1. **The bot's offset.** The dry v3.0 family already logs it on the box:
   `sudo python3 ~/v2pons/deploy/englog.py 24 | grep '"ev":"first_buy"' | grep '"fee":10000,' | grep -o '"offset":[0-9]*' | sort | uniq -c`
   - Today the offsets run from 18 to 61, and no 3 adjacent values hold more than about 1 pool in 5.
   - Reopen the study if 80% of a day's offsets fall in 3 adjacent values.
2. **Other people's fronts are free probes.** If any 3.0 pool where a stranger bought 0.00003 ETH or more before T still gets a bot
   buy, condition 2 has changed.
   - Run `python3 research/session_oct11/vbot_recent.py 180` from a dev machine, on the public RPC.
   - It lists, per pool, the strangers ahead of the bot, T and the pull.
   - Its "decoy" label is wrong (see REPORT_R), but its T and pull columns are right.

## What was checked

| Study | 3.0 pools | Window (UTC, Oct 11-12) |
|---|---|---|
| Finder, precursors (all txs in T-12..T+3, logs in T-4..T) | 200 (discovery 133 / held out 67) | 09:38-21:44 |
| Finder, schedule (30,910 bot actions on all lines) | 244 3.0 of 509 (held out 82) | 11:32-21:32 |
| Skeptics, rule 1 | 116 + 49 | 04:22-09:18, 20:41-22:41, 21:38-22:35 |
| Skeptics, rule 2 | 121 + 48 (+67 older) | 04:30-09:37, 21:31-22:49 |
| Skeptics, rule 3 (whole blocks L-3..T, receipts, a live block-by-block watch) | 91 + 58 | 04:21-09:38, 21:38-23:48 |
| Skeptics, rule 4 | 180 + 49 | 04:21-09:38 and Oct 4 14:18-18:30, 21:45-23:53 |
| Skeptic, rule 6 | 48 | 22:28-00:18 |

In all, about 370 current-regime pools from 04:21 Oct 11 to 00:18 Oct 12.

Gaps:
- **The reaction angle was stopped early.** The reaction figures above come from REPORT_R and from three skeptics' own chain counts.
  They agree.
- **Rules 5 and 7-10 had no dedicated skeptic.** They lose on the finders' own held-out pools, and the skeptics' side checks agree.
- **Untested:** how fast the pull follows a buy that lands in T-2..T, because nobody has bought there.

**Files.** Everything is under `research/session_oct11/lines/analysis/T3/`:
- `precursor/` and `schedule/`: the finders;
- `reaction/`: unfinished;
- `skeptic1_*/` and `skeptic2_*/`: the verifications.

Large caches and pickles (`precursor/cache/`, `*.pkl`, `pools*.json`, `*/cache/`) are rebuilt from the chain and should stay out of
commits.
