# p356 re-check B: the 356-B launches stopped; the longer calls are the same code's value launches, and the rule has no edge on them

(An Opus analyst's report, Oct 12 ~11:30 UTC, saved by the session.)

Window: blocks 84,960,346 .. 86,635,957 (Oct 10 11:24:37 .. Oct 12 11:24:37 UTC). Source: the public RPC only, read methods only, one
POST at a time at least 0.5 s apart (`rpc.py`, a copy of analysis/W/rpc.py). Load: 530 POSTs, 4,432 items, 0 transactions sent.
Census numbers come from census 2's cache (Oct 4 13:52 .. Oct 11 13:52 UTC) and were replayed with the same code. Scripts p01..p11 are here;
each `.out` file is that script's printout. The raw dumps (p04_events.jsonl, p05_txs.jsonl, p10_swaps.json) are not committed.

## 1. Launches by launcher code 89885b75 (p01-p03, p10, p11)

The V3 factory logged 542 PoolCreated events. 102 came from a tx whose `to` has code keccak `89885b75…08a`. In all 102: selector
`d27d1e00`, status 1, priority fee 1 wei, exactly one pool per tx.

| calldata | n | value (ETH) | arrays N | first .. last (UTC) |
|---|---|---|---|---|
| 356 B | 57 | 0 | 0 | Oct 10 17:02 .. **Oct 11 19:56:38** (block 86,094,707) |
| 420 | 2 | 1.0 | 1 | Oct 11 16:25 .. 16:28 |
| 548 | 10 | 5-15 | 3 | Oct 10 12:19 .. Oct 11 21:54 |
| 612 | 7 | 6-18 | 4 | Oct 11 13:42 .. 17:36 |
| 676 | 11 | 3-15.3 | 5 | Oct 11 16:33 .. Oct 12 04:51 |
| 996 | 9 | 7, 12.7 | 10 | Oct 10 13:58 .. Oct 12 10:50 |
| 1124 / 1636 / 1828 | 1 / 1 / 4 | 15.3 / 18.01 / 20.0-20.01 | 12 / 20 / 23 | Oct 11 20:08 .. Oct 12 10:10 |

Six-hour slices from Oct 10 11:24: 356 B 7/0/18/0/12/20/0/0. Other lengths 2/0/2/0/15/9/5/12.

- **The 356-B value-0 launches did stop** after Oct 11 19:56:38 UTC. In the 15.5 h since, this code made 21 launches (32.6 a day), all of
  them value launches: 548 B x2, 676 x5, 996 x8, 1124 x1, 1636 x1, 1828 x4, carrying 3 to 20.01 ETH.
- **The longer calls are not a new form of the 356-B line.** They are the value launches this code has sent all along: 128 of its 248
  census launches (lengths 420-1828), and 24 in this window before the stop.
- **No other launcher took the line over.** A chain-wide Mint search for the exact range -887272..207243 over the 48 h found 104 Mints:
  102 are these launches, 2 are another wallet's PositionManager pools (0xd974f9e5, `13ead562`) on Oct 11 at about 05:00; after the stop,
  21, all value launches of this code. The fleet's fingerprint appears in none of the 102 other V3 WETH pools created after the stop (to
  +600); those pools had 18 router buys of 0.05 ETH or more, none the fleet's.

**What the extra calldata carries:** more buyers in the launch tx, not more tokens and not a different mint. The call is
`d27d1e00(token, holder, ethFirst, holder, address[] buyers, uint256[] amounts, 0, holder, 0)`:

- **Length:** 356 + 64·N bytes in 102 of 102 here and 248 of 248 in the census. The two array offsets are 0x120 and 0x140 + 32·N.
- **Value:** word 2 + Σ amounts in 102 of 102.
- **The holder (words 1, 3 and 7, the same address in 102 of 102):** receives the position NFT (102 of 102); is the puller (34 of 34
  pulls on 356-B pools, 8 of 8 on value pools); is never the launch wallet.
- **The launch tx's buys:** N + (word 2 > 0) SwapRouter02 `exactInputSingle` buys, with the router as the Swap sender (102 of 102): first
  the word-2 buy, sent to the holder (29 launches); then amounts[i] to buyers[i], in order. buyers[0] is the launch wallet in 45 of 45.

**Receipt.** For both shapes (57 of 57 and 45 of 45 here, 111 of 111 and 128 of 128 in the census): one pool, WETH as token0, fee 100,
tick spacing 1; Initialize at tick 207,243; one Mint by the PositionManager, of the token alone (amount0 0, amount1
999,999,999,999,999,999,999,981,671), range -887272..207243, L **31,622,807,953,636,212,567,716**.

The value launches differ only by their swaps. Per launch (p10/p50/p90) they have 4/5/21 swaps buying 5.0/12.0/18.0 ETH. After them the
tick is 148,342/155,943/171,407, so the token price is x361/x169/x36 the launch price. By +60 the tick has moved only -2/-1/0.

## 2. The value launches' flow (45; 40 after the census) (p06, p11)

| | value launches (48 h) | 356-B launches (48 h) |
|---|---|---|
| Pools with a fleet buy* | 42/45 (93%) | 19/57 (33%) |
| First fleet buy, p10/p50/p90 (block offset) | +201/+314/+462 (earliest +181) | +107/+165/+368 |
| Fleet buys per pool, to +600 | 9/22/47 | 5/15/71 |
| Fleet ETH per pool, to +600 | 1.56/4.05/8.53 | 0.55/1.85/7.37 |
| Pools with a fleet buy inside the hold (+60..+259) | 13 (median 0 buys) | 16 (median 8 buys, 1.08 ETH) |
| Sells by the launch-tx wallets, to +600 | 32 pools; first +209/+371/+516; 0.41/4.81/8.29 ETH out | 7 pools, dust |
| Launch-position pulls, to +3000 | 8/45 at +609, +967, +1706, … (none at or before +600) | 34/57; p10/p50/p90 +310/+1113/+1941; 2 at or before +260 |

\* A fleet buy is SwapRouter02 `04e45aaf`, 228 B, ETH as value, priority 1, not from an operator wallet. Fleet buyers: 782 of the 1,051
buys come from a wallet seen in one pool only, and the buyer's nonce has a median of 9.

- **Pulls** are full in every case, via a PositionManager multicall of 900 B, sent by the holder. In the census, 2 of 128 value launches
  were pulled within 3,000 blocks.
- **Outside buys of 0.0005 ETH or more at +1..+59** (the test from REPORT_V23): value launches: 8 pools, all bot dust (`0x65050a9b`
  `4d819a2a`; at most 0.00099 ETH), all 8 pumped anyway against 34 of 37 without one; the rule made +1.38% with one and +0.14% without; no
  sign of deterrence, but n is 8. On the 48 h 356-B set the census's contrast (14% pumped against 48%, p 0.0002) does not show with this
  script's classes: 7/24 against 12/33 (p 0.78); after the census 4/17 against 4/15.

## 3. The rule: buy 0.0058 ETH at +60, sell at +260 (C's V3Sim; net of $0.02 gas; a pull at or before the sell counts -100%)

| set | n | mean | median | win | pulled | $/day at $15 | at $5: mean / median / $/day |
|---|---|---|---|---|---|---|---|
| census 356-B, value 0 (REPORT_V23)¹ | 111 | +114.97% | +0.060% | 53.2% | 1.8% | 271.8 (7 d), 787.1 (days 6-7) | +116.75% / -0.205% / 92.6, 268.5 |
| 48 h 356-B, value 0 | 57 | +46.05% | +0.282% | 77.2% | 2 | 195.6 | +47.06% / +0.019% / 67.1 |
| … of them after the census (Oct 11 13:52-19:56) | 32 | +27.23% | +0.240% | 75.0% | 1 | – | +28.42% / -0.021% / – |
| **48 h value launches** | **45** | **+0.36%** | **-0.140%** | **15.6%** | **0** | **1.2 (1.8 at the post-stop rate)** | **+0.10% / -0.405% / 0.1 (0.2)** |
| census value launches | 127 | +0.90% | -0.151% | 19.7% | 0 | 2.4; days 6-7 n 31, -2.05%, -4.7 | +0.64% / -0.417% / 0.6 |

¹ Re-run here from census events with C's float replay; it matches REPORT_V23 to the cent.

- **On 356-B pools** the fleet buys into a pool nobody has bought, from about +107; its buys land in the hold and the return comes from
  them: in the 48 h set the 19 pumped pools made +148% and the 38 others -5.0%.
- **On value pools** the launch tx has already lifted the price 36-361x; the fleet arrives after +260 in 29 of its 42 pools, and the
  launch-tx wallets sell into it, 4.8 ETH (median) by +600. The rule's median is gas and fees and the mean about zero in both samples.
- **A lead, not a rule** (p08, p09; the buy +60 / sell +600 cell was picked after looking, from a 30-cell grid): 48 h value launches
  +12.18% mean, +5.37% median, 60% win, 0 pulled (at $5 +11.96%, about $19.5 a day at the post-stop rate); census value launches, out of
  sample (n 127): +11.7% mean, +0.03% median, 51% win, 0 pulled; by day +6.5/+7.4/+55.3/+12.5/+6.8/-4.4/+29.4%. The +600 sell is 9 blocks
  before the earliest 48 h pull (+609), and pulls rose from 2 of 128 (census) to 8 of 45 (48 h). Dry-run material at most.

## 4. Engine

**Do not widen p356 to the value calls.** On them the line's rule is worth about $0.2 a day at $5 (median -0.4%), in both the 48 h sample
and the census. Keep the family as it is: selector `d27d1e00`, `calldata_len` 356, `value_wei` 0, the full code hash; one pool per tx; the
pin (L 31,622,807,953,636,212,567,716, range -887272..207243, width 1,094,515, Initialize at 207,243, one Mint, WETH as token0, fee 100,
tick spacing 1). While the shape is paused the dry run logs nothing; if it returns, the family catches it unchanged.

If the value launches are wanted (for example a separate dry family to test the +600 lead): (1) selector and code hash unchanged;
(2) length 356 + 64·N with N >= 1 (N 1..23 seen, 420-1828 B; the census adds 484, 740, 868, 932, 1188, 1764), better by decoding words 4
and 5 as 0x120 and 0x140 + 32·N with both arrays of length N; (3) value > 0 and equal to word 2 + Σ amounts (the census also had 9 calls of
356 B with value 0.1-0.5 ETH: N 0, one word-2 buy, +228% on 9 trades over days 1-5; none in these 48 h); (4) one pool per tx; (5) the pin
unchanged; (6) the arming price from the launch tx's last Swap (sqrtPriceX96, tick; the in-range liquidity is still the one L), not from
Initialize, else the price copy starts x36-361 off, keeping the fingerprint's check that Initialize is TickMath(207243); (7) the pull watch
unchanged (the holder, word 1, owns the NFT and pulls with a 900 B PositionManager multicall); (8) no change for "ahead ETH" (a taken launch
call returns from `ingest_tx` before `state["recent"]`; others' ETH at +1..+59 reached at most 0.0075 ETH).

**A $5 probe once the V3 route exists:** on the 356-B line only if the 356-B launches come back (none in 15.5 h); the latest 32 were
already thinner than the census (at $5 +28.4% mean, -0.02% median, 8 of 32 pumped, the top 10% of trades more than 100% of the return);
REPORT_V23's gate and halts still apply. On the value launches with +60/+260: no.

What the sample allows: 45 value launches over 48 h (40 after the census) and 57 356-B launches (32 after the census); swap txs fetched to
+600 only; the +600 cell is a post-hoc pick.
