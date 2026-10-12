# BNB Chain launch lines (census Oct 4-11, verified Oct 12)

**Inputs.** The PancakeSwap grid is the only new one. The four.meme, Uniswap v4 and flap grids are earlier finished results, used as they were (not re-run). The verdicts passed to me end after the 83c620 replay vote, so the other PancakeSwap verdicts below are read from the lens outputs in `verify/`.

## 1. Chain facts
- **Endpoints**
  - nodereal (shared public key): 50,000-block log calls, 30M blocks of history.
  - sentio, pocket and blockmachine: 10,000 blocks per call, full archive.
  - publicnode: about 10,000 blocks of history, but the best pending feed.
  - Blocks come every 0.4503 s.
- **Launchpad maths**, replayed exactly:
  - four.meme: a virtual curve with a 1% fee plus a 2-10% tax each way. On 368 launches an anti-sniper fee runs from 100% at +0 down to 5% at +5.
  - flap: 1% fee plus tax, with no anti-snipe charge.
  - PancakeSwap V2: 25 bps; 99.92% of swaps replay exactly.
- **Visibility.** 60.9% of transactions were seen pending, with a median lead of 0.161 s, never 2 blocks ahead. Seen pending: 0x07cb6161 18.9%, 0xa3e0e540 45.4%, flap Portal 46.1%, four.meme TM2 18.2% (19% of TM2 never seen, so private). No pending front anywhere.
- **The gap**, in blocks from the launch to the operator's buy:
  - 0x07cb6161: +6 at the median (+11 after the census)
  - 0xa3e0e540: +55 after the liquidity
  - 0xc9b7cc61: +60 at the earliest, +77 at the median
  - flap pump0715: +126
  - four.meme USDT crowd: +0, bundled with the launch
- **Competition in the first blocks**
  - flap: 1,007 of 2,122 traded launches had a sniper by +1, paying 0.35-2 gwei.
  - four.meme: 31 of 254 had a buyer by +3.
  - PancakeSwap V2: 16 of 1,725 had a buyer by +3.

## 2. Census (7 days)
| venue | launches | traded | real buy | pulled/drained | families ≥20 | grid result |
|---|---|---|---|---|---|---|
| four.meme | 43,592 | 2,533 | 1,081 | 1,709 | 128 | no line (fees leave −6 to −8%) |
| flap.sh | 86,800 | 24,987 | 18,272 | 22,008 | 319 | 11 candidates |
| Uniswap v4 | 8,553 | 2,801 | 1,320 | 2,036 | 26 | no line |
| PancakeSwap V2 | 99,191 | 12,575 | 11,429 | 8,184 | 672 | 12 candidates |

## 3. Survivor: launcher 0xc9b7cc61
Selector 50b6f139, about 177 launches a day. This line covers candidate 9f0350 and its parent 83af7929, which the grid had rejected. It is still running: 51 launches in the 6.5 h after the census.

**Why the grid rejected it, and why that was wrong.** The grid assumed that buying ahead of the crowd makes its buys revert. But the crowd sets its minimum output at 0.9999 of the price just before each buy (11,872 of 11,982 fetched buys). A buy one or more blocks ahead caused 1 revert in 1,242 launches.

**Rule.** Buy $15 at L+60 (L+40 to L+58 gives the same result) and sell at L+260.

| pool size (BNB) | launches/day | mean | median | win rate | validation mean | $/day |
|---|---|---|---|---|---|---|
| 1 | 8.0 | +121.2% | +102.4% | 98% | +97.4% | 145.3 |
| 10 | 10.8 | +35.8% | +34.8% | 99% | +40.3% | 58.2 |
| 25 | 22.6 | +8.6% | +8.3% | 98% | +8.6% | 29.1 |
| 2.5 | 45.4 | +10.9% | +7.6% | 77% | +11.5% | 74.3 |
| 15 (skip) | 90.5 | +1.4% | +1.2% | 74% | +1.7% | 19.6 |

- **Without the 15-BNB pools:** mean +23.6%, median +11.1%, $306.9/day ($264.5/day in validation). All 28 six-hour slices are positive. The 47 launches after the census made +14.5%.
- **Who moves the price:** 136 crowd accounts buy 509.8 BNB during the hold, through router 7ff36ab5. Strangers buy 0.15 BNB.
- **The creator** never buys. It dumps on a fixed schedule by pool size:
  - 1 BNB: +997 to +1,420
  - 10 BNB: +2,028 to +2,255
  - 2.5 and 15 BNB: about +4,000
  - 25 BNB: about +6,800

  None of 60 live pools was dumped before +1,000.
- **Competition at entry:** only 4 of 290 pools had any swap between +50 and +62.
- **Reaction to strangers:** none seen. After 17 stranger buys of $1 or more, crowd buying sat at the 42nd percentile of matched controls, and the dumps kept their schedule.
- **Execution:** swapExactETHForTokens at 0.1 gwei. Gas is about 370k per round trip ($0.028). On-chain round trips: 20 of 20 succeeded, no token tax.
- **Top risk:** only 9 strangers bought $5 or more. The 1-BNB pools carry 44.5% of the profit, have no such case, and our $15 is 2% of one of those pools.
- **Files:** `verify/*9f0350*`, `verify/*83af7929*`, `report/out/s1_survivor_tiers.json`.

## 4. Refuted
| candidate | lenses that refuted it | reason |
|---|---|---|
| 0x07cb6161, 6.17 BNB (aff2095) | all 3 | 618 of 618 stranger buys were pulled within 8 blocks, including the one stranger who bought before the crowd. About −100%. |
| 0x07cb6161, 17.6 BNB | all 3 | 269 of 269 strangers were pulled on. Even selling just before the pull nets only +1.7%. |
| 0xa3e0e540 (83c620 and its parent) | all 3 | 24 of 24 strangers inside the hold were pulled 1-5 blocks later. −82% to −100%. |
| 0xba56663c (7271cef6) | replay, reaction | 21 of 23 outsider buys of $11+ were drained within 200 blocks (20% otherwise). −78% at $15; +40% at $5, below half the claim. No launch since Oct 11 13:31. |
| bc444b09, 8bff9d33 | all 3 | Pulled after 60 of 60 and 50 of 50 strangers. These rules break even only if fewer than 7.3% and 5.4% of our buys trigger a pull. |
| b5e0fa10 | all 3 | A wiper contract zeroed the balances of 14 of 14 outsiders 1-4 blocks after they bought. |
| flap pump0715 | all 3 | Our +80 buy is the early stranger that cancels the pump. +1.6% to +16%. |

**Not verified:** 5ec1c2 (died in validation), 5c11d795 (USDT honeypot) and the flap v7 line (+10.2%, $27/day).

## 5. Recommendation
Build a small BNB engine for 0xc9b7cc61. Start with the 1, 10 and 25-BNB pools, then add 2.5.

- **Entry:** buy between L+40 and L+58, ahead of the scheduled crowd. There is no pending gap; we act once the launch block is seen.
- **Gate:** probe at $5. Halt the line on any of:
  - a dump before +997
  - no crowd buy between +60 and +260 (the crowd came in 290 of 290 1/10/25-BNB pools)
  - a revert
  - a negative median over the first 10 probes
- **Build list:**
  1. Block and log reader. A mempool reader is optional, for monitoring only.
  2. Router calls from our wallet at 0.1 gwei.
  3. Approve, then swapExactTokensForETH.
  4. Per-line halts.
  5. A weekly census re-run.
