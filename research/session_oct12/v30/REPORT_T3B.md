# REPORT_T3B: the 3.0 line re-checked after 2.433 stopped (Oct 12, 05:38-17:37 UTC)

Verdict: **STILL UNTRADABLE**. One analyst (no skeptic: nothing tradable to verify).

## Timing

The bot's first buy is still random. It sits at L+17 to L+61 in 481 of 491 pools, and nothing about it changed when the 2.433 line stopped.

Scope: all 491 3.0 launches from 05:38:09 to 17:31:01 UTC Oct 12, out of a 12-hour window to head 86854728 (17:37:04). Every one matched value 3 ETH, the PositionManager, 1,444 B multicall, fee 10000 / tick spacing 200 and the 3.0 sqrtP. In every pool, T's tx was to the bot router 0x1cbaf24d with selector c1120e3d.

**T-L across all 491 pools**
- min 17, p10/p50/p90 27/41/55, max 150.
- The 10 outliers are at L+62 to L+150.
- In seconds, T-L is 2-6 s (p50 4).

**Per hour** (n: p10/p50/p90; best ±1 window; best ±2 window):
- 05h 10: 36/43/52; 40%; 40%
- 06h 17: 29/40/53; 23.5%; 29.4%
- 07h 34: 26/44/55; 14.7%; 23.5%
- 08h 139: 23/40/54; 12.9%; 18.7%
- 09h 98: 28/40/55; 15.3%; 23.5%
- 10h 42: 24/43/55; 16.7%; 21.4%
- 11h 33: 22/39/55; 15.2%; 21.2%
- 12h 30: 27/42/57; 13.3%; 23.3%
- 13h 19: 27/41/58; 21.1%; 26.3%
- 14h 32: 32/43/54; 21.9%; 31.2%
- 15h 14: 34/45/57; 21.4%; 28.6%
- 16h 14: 31/44/52; 21.4%; 28.6%
- 17h 9: 28/43/66; 22.2%; 33.3%

The higher hourly shares come from small n. Over all 12 hours the best ±1 window is L+35..37 with 56 of 491 pools (11.4%). The best ±2 window is L+41..45 with 84 of 491 (17.1%).

**Held out** (window picked on one half, tested on the other; first/second half and even/odd hours):
- ±1 window: 7.4% to 11.4%.
- ±2 window: 14.3% to 15.7%.

**Regime change: none in T.** The distribution matches Oct 11 (26/40/53).
- Launcher class moves the median by 4 blocks (nonce-3 fresh-chain wallets p50 43, nonce-268+ wallets p50 39; r 0.20).
- Nothing else known at L predicts T, all |r| ≤ 0.07: sentinel offset, 0x7ae81404 offset, deploy→L gap, launch tx index, previous pool's T, L mod 10.

**What did change is pool life.**
- 336 short pools: pulled at T+91..154 (median T+121), with a median of 5 bot buys and 0.81 ETH. They ran mostly from 07h to 12h and at 14h; the 08-09h spike is 132 + 88 of them.
- 155 long pools: pulled around T+5,500, median 119 bot buys and 17.25 ETH, steady at about 7-16 an hour.
- T-L is identical in both types (27/41/55).

**Bot buys / ETH per pool** (mean; median buys in brackets):
- 05h 83.7 / 12.78 (109)
- 06h 96.1 / 14.56 (113)
- 07h 40.6 / 6.32 (6)
- 08h 10.8 / 1.77 (5)
- 09h 16.4 / 2.69 (5)
- 10h 41.5 / 6.30 (6)
- 11h 44.1 / 6.76 (6)
- 12h 56.2 / 8.44 (21)
- 13h 82.6 / 12.28 (105)
- 14h 51.7 / 7.76 (38)
- 15h 108.6 / 16.62 (123)
- 16h 116.2 / 17.97 (125)
- 17h 83.8 / 12.92 (74)
- all hours: 38.6 / 5.95 (6)

The bot's first buy is p10/50/90 0.075 / 0.148 / 0.198 ETH.

## Reaction

The early-buy pull has not been shown to stop, and the one buy that landed ahead of the bot was still followed by a pull 6 blocks later. The bot bought in all 491 pools. Only one pool had a non-dust stranger buy before or at T, and nobody bought non-dust at T-1 or earlier in 12 hours, so the case that matters (a buy before T) could not be observed at all.

**The one fronted pool:** L 86738069, launched 14:18:34.
- 0xed165972 bought 0.000395 ETH through the Universal Router (tx 0x434785d9...) in block T itself (L+32, block 86738101), at log index 8.
- The bot's buy (0.198 ETH, tx 0x59aa9f6b...) came after it in the same block, at log index 10.
- The bot bought only that once.
- The pool was pulled at T+6 (block 86738107, tx 0x8fa5aa2f...), 6 blocks after the stranger's buy.
- For comparison, of the 415 pools with no non-dust stranger buy at all, all but one lasted at least T+68 (pull-T p10 108, median 126). The one exception, 08:37:52, was pulled at T+8 with no visible trigger.
- So a buy that lands in block T ahead of the bot still gets the bot's buy, and the pull follows about 6 blocks later.

0xed165972 is not a front-runner. It made 20 identical 0.000395 ETH buys in 3.0 pools from 14:18 to 14:22, at L+32..413, and never sold any of them. Two of those buys happened to land in the same block just ahead of a bot buy.

**Dust buys before T draw nothing:**
- The 2e-6 sentinel 0xe71a69f4 bought in all 491 pools, at L+3 in 403 of them.
- 0x7ae81404 bought 1e-5 to 2e-5 ETH at L+1..3 in 400 pools. On Oct 11 it bought 0.00297 ETH and was pulled every time; it now stays under the 0.00003 line.
- 0xb8c879dc bought 1.2e-5 ETH in 80 pools.

**After T** (75 pools with a non-dust stranger buy; pull lag after the first one p10/p50/p90 7/16/3,766):
- Buys of 0.0001 ETH or more: 51 of 53 pools were pulled within 30 blocks.
- Buys of 0.00003-0.0001 ETH: only 7 of 22 were pulled within 30 blocks.
- 0x8cf143dd, the former 2.433 decoy, bought 0.000049 ETH at L+51..53 in 9 pools without drawing a pull.
- Pools pulled within 30 blocks almost always got just 1-2 more bot buys.

There were no early sells.

## Rule

No window and no signal works, so there is no rule and no family settings to give.

| | Held-out in-time share | Needed |
|---|---|---|
| Best fixed ±1 window | 7.4%-11.4% | 94% |
| Best fixed ±2 window | 14.3%-15.7% | 94% |
| Best signal (UR execute via 0xf533b2c4) | 16.7% of fires (2 of 12) | 94% |

In-time means our buy lands in T-1..T.

**Signal tests.** Every tx in blocks L+12..T of 212 pools: 94 for discovery (every 4th pool, 05:38-11:59) and 118 held out (every pool from 12:00 on). A rule arms at L+15 or L+25, fires on the first occurrence, and our buy lands 1 or 2 blocks later. The candidates were frozen from discovery before the held-out test.

1. **Any tx to the bot router.** Present in T-4..T-1 in 21 of 94 and 21 of 118 pools. The background is 4.2-4.4% per block, about 16% expected over 4 blocks. Held out: 2.5-4.5% of fires in time. The log-based version over all 491 pools (another pool's bot buy at T-1..T-4) shows 4.5-6.3% against a 4.1% background, and 2.9-4.7% of fires in time.
2. **Any tx from a bot buyer wallet (177 wallets).** 30 of 94 and 29 of 118 pools, against a background of 7.8-8.1% per block. Held out: 3.8-8.8% of fires in time.
3. **The three data-mined keys:**
   - UR execute via 0xf533b2c4: 5.9-16.7% held out.
   - 0x581e04e1 dbb80a68: 3.6-9.1%.
   - 0xc8914bbb ae7e8d81: 4.2-7.4%.
4. **Anything tied to the pool:** nothing mentioning the token or T's buyer, nothing sent to them, and nothing from the launcher in T-4..T-1, in 0 of 94 and 0 of 118 pools. T's buyer sends nothing between L+12 and T-1.

With 2.433 gone, the bot router is quieter, but its activity is still background noise with no lead to T.

**Keep v3.0 dry.** Its current settings (fire_at 12, fire_max 3) land at about L+13..17, which is T-1..T only when T-L is 14-18 (3 of 491 pools, 0.6%). Live, nearly every fire would be an early buy, which gets pulled at -100%. The dry family's +6.8% cannot be achieved live.

## Evidence

**Head and sources**
- Head frozen at 86854728 (17:37:04 UTC Oct 12); events read to 86856987.
- 491 3.0 launches: 05h 10, 06h 17, 07h 34, 08h 139, 09h 98, 10h 42, 11h 33, 12h 30, 13h 19, 14h 32, 15h 14, 16h 14, 17h 9.
- Every pool has T and every pool was pulled once, by the PositionManager.
- T = the first Swap whose tx also moves the pool token from the PoolManager into the bot router. In all 491 pools that tx was checked to be to 0x1cbaf24d with c1120e3d.

**RPC**
- Public RPC only, paced through research/session_oct12/c1/rpc.py (one POST at least 0.5 s apart).
- 4,048 POSTs (66,508 items), read methods only: getLogs, getBlockByNumber, getTransactionByHash, getTransactionReceipt, getTransactionCount, getBalance, blockNumber.
- No key, no transaction, nothing committed. src/, deploy/, tests/ and docs/ were not touched.

**How the blocks were read**
- Hashes only, from 3,876 blocks.
- The 48 KB oracle push to 0xd7572f7e at index 1 of each block was identified from its receipt and not downloaded.

**Fronted pool, block by block** (L 86738069, T 86738101)
- Front tx 0x434785d9a04e03ae0c80e0e27056bea0c9b7bfbb1aa9d386727f0e7bc47a6445 at log 8.
- Bot tx 0x59aa9f6b86e0f8eba28e5d4c1017cd7ed2dfb4845f3d803866ca6a0289d09182 at log 10.
- Pull tx 0x8fa5aa2feeb68c37e3252532cfcf1a06bd5dbf1cbd044718690c42d1a3333f0f in block 86738107.
- 0xed165972 is at nonce 8799 with 0.00538 ETH, and has made no sells of these tokens.

**Limits**
- With only one non-dust buy ahead of the bot (in block T) and none at T-1 or earlier, we cannot tell whether the bot would still buy after a buy landing at T-2..T-1.
- The precursor scan covers txs only (from, to, selector, address words in the input). It does not cover receipts or logs of other contracts.
- The other-pool bot-buy series from logs also counts the few pulls.
- No .md report was written, by instruction. The findings are in this answer.

## Files

All scripts and outputs are under /home/user/v2pons/research/session_oct12/v30/timing/. Raw caches are *_cache.jsonl (git-ignored), split into _pNN parts so no file is over 2 MB.

Scripts:
- vc.py: helpers, paced through research/session_oct12/c1/rpc.py.
- v01_launches.py: the 3.0 launches.
- v02_events.py: per-pool swaps and ModifyLiquidity, and transfers into the bot router.
- v03_build.py: per pool T, bot buys and ETH, pull, and buys before T.
- v04_timing.py: per-hour T-L, best windows, held-out windows, seconds.
- v05_reaction.py: buys before T and pull lags.
- v06_blocks.py: all txs in L+12..T for 212 pools.
- v07_botlog.py: other-pool bot buys as a lead, all 491 pools.
- v08_features.py: features known at L.
- v09_precursor.py: discovery, frozen candidates in v09_candidates.json, held-out test.
- v10_after_T.py: stranger buys after T, and the 0xed165972 wallet.
- v11_botrate.py: bot activity around L and T.
- v12_life.py: short and long pools per hour.

Key outputs:
- /home/user/v2pons/research/session_oct12/v30/timing/v04_timing.out
- /home/user/v2pons/research/session_oct12/v30/timing/v05_reaction.out
- /home/user/v2pons/research/session_oct12/v30/timing/v09_precursor.out
- /home/user/v2pons/research/session_oct12/v30/timing/v10_after_T.out
- /home/user/v2pons/research/session_oct12/v30/timing/v12_life.out
- /home/user/v2pons/research/session_oct12/v30/timing/v07_botlog.out
- /home/user/v2pons/research/session_oct12/v30/timing/v08_features.out
- /home/user/v2pons/research/session_oct12/v30/timing/v11_botrate.out

Data:
- /home/user/v2pons/research/session_oct12/v30/timing/v03_pools.json: per pool L, T, T-L, bot buys and ETH, pull, buys before T.
- /home/user/v2pons/research/session_oct12/v30/timing/v05_fronted.json
- /home/user/v2pons/research/session_oct12/v30/timing/v06_sets.json
- /home/user/v2pons/research/session_oct12/v30/timing/v01_meta.json
