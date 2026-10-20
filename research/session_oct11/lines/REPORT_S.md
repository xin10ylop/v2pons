# Analyst S: the V3 self-buyer lc:0a493d1a|13ead562 re-replayed, Oct 12 07:00 UTC

**Verdict:** the line is back: 7 of the last 8 launches carry the launcher's own 0.05 ETH buy. But it is about 50 times smaller than the
census: 8 launches in 24 h, and the pools are much deeper. Rule (a) wins every trade in the sample, at a mean of +12.3%. At $15 that is
**$14.5/day** at 24 h volume, or $44.5/day if the rate of the last 6 h holds (the census figure was $678/day). The late timing rests on 4
launches. Nothing in 50 h tests how the operator reacts to a buy ahead of its own; the one precedent (Oct 9) is the operator stopping its
buy after it was sniped twice. Hold the $5 probe until the gate below passes.

Data: the public RPC only (s01 head 86,480,222 = 06:57:35 UTC), 50 h of factory PoolCreated, ~200 polite posts, no 429 storms. Simulator:
C/replay.py V3Sim. It reproduces the launcher's own buy to within 2.3e-12 (69 of 69). ETH is priced at $2570 and gas at $0.02 per round
trip, both as in REPORT_C. Scripts and outputs are in analysis/S/ (s01-s09, `scommon.py`).

## The line now
- **Launch:** `createAndInitializePoolIfNecessary` 13ead562 (132 B, value 0) sent straight to the NonfungiblePositionManager 0x73991a25. Its
  code hash is 0a493d1af3d0…: the "launcher contract" is the PositionManager itself.
- **Sequence:** the wallet sends 4 txs with consecutive nonces (the dEaD transfer was missing in 2 of the 13 launches checked, s08):
  1. the launch (n);
  2. `mint` 88316456 (356 B, value 0): one token-only range [-887272, 204200] (3 of 70 mirrored, WETH as token1), recipient the
     launch wallet, mins 0, deadline the launch + 1200 s;
  3. `transfer` of 3e5 tokens (6.67e8 at the 1.227e22 tier) to 0x…dEaD;
  4. its own buy: SwapRouter02 `exactInputSingle` 04e45aaf, 228 B, value = amountIn, minOut 0, recipient the launch wallet (101 of 101).
- **Line launches** (fee 100, that mint shape; 4 other 13ead562 launches excluded, s04):
  - 6 h: 7 (28/day);
  - 24 h: **8 (8/day)**, 7 of them since 02:06 today;
  - 48 h: 70, of which 46 fell in one burst at Oct 11 00:10-00:28 (wallets 0x0344a29a ×20 and 0xfe94166e ×26; 45 of the 46 had a
    0.001 first buy).
- **The own first buy:**
  - 24 h: 0.05 ETH ×7, 0.001 ×1 (the second launch of wallet 0xf41e1a64).
  - 48 h: 0.001 ×47, 0.05 ×19, 0.01 ×3, none ×1.
- **Its offset, last 24 h (0.05 buys):** +25, +25, +27 (old timing, mint at +6/+7), then **+138, +140, +142, +184** in the last 4 launches
  (since 05:23). In those 4, every step is slower:
  - the mint is at +28..+32 (+3 s), against +4..+8 (+0..1 s; one at +15) on the other 66;
  - the transfer to dEaD is at +52..+55;
  - the buy follows the transfer by 85/86/90/129 blocks (9/9/8/14 s), against 11..19 blocks (1-2 s) in the 7 Oct 11-12 launches
    before them;
  - measured from the launch: +14/+14/+15/+20 s.

  The watch's "+138..+142 in 5 of 6" is really 4 launches (its scanner only looks 150 blocks out, so it missed the +184 one).
- **Other swaps to +400, last 24 h:** none before the own buy. After it, 8 buys of 0.023-0.075 ETH at +146..+389 by EIP-7702 accounts
  (self-calls 34fcd5be, 708 B, paid in WETH; delegate 0x69007702…), and 2 dust buys via 0x65050a9b. In 48 h there was no outsider buy
  before the own buy in 70 of 70 launches.
- **Pulls** (Burn, by the launch wallet via a PositionManager multicall):
  - 24 h: 2 of 8, at +279 (after its own 4×0.005 buys) and at +1681.
  - 48 h, 0.05 class: 10 of 19, earliest +242.
  - 48 h, 0.001/0.01 class: 48 of 50, 44 of them at +44..+187 (median +74).
  - None before the own buy.

## Replay (s06; buy at the head of L+a, sell at the head of L+b; a pull at or before L+b counts as -100%)
The 24 h window has 8 launches. Every $/day figure in this table uses the 24 h rate of 8/day.

| rule (24 h, n 8) | mean | median | win | pulled | $/day at $15 | $/day at $5 |
|---|---|---|---|---|---|---|
| (a) mint+2 → own buy+1, cap +200 | +12.3% | +7.4% | 1.00 | 0 | $14.5 | $4.8 |
| (a) with the sell at own buy+3 | +12.3% | +7.4% | 1.00 | 0 | $14.5 | $4.8 |
| (b) own buy−2 → own buy+1 (oracle) | +12.3% | +7.4% | 1.00 | 0 | $14.5 | $4.8 |
| (c) mint+2 → +160 | +12.3% | +7.4% | 0.88 | 0 | $14.6 | $4.8 |
| (c) mint+2 → +200 | +15.3% | +8.2% | 1.00 | 0 | $18.1 | $6.1 |
| REPORT_C's rule (first buy ≥0.005 +1, cap 60) | +6.6% | +0.1% | 0.50 | 0 | $7.8 | $2.5 |

- **The last 6 h** (n 7, 28/day): rule (a) makes +10.8% mean, 1.00 win, **$44.5/day at $15 and $14.8 at $5**.
- **48 h** (n 70, 35/day):
  - (a): +3.5% mean, +0.1% median, 0.99 win, 0 pulled; $17.5 / $5.5 a day.
  - (c) +200: −58.2% mean, 44 pulled (the 0.001-class pulls).
  - REPORT_C's rule: −8.5%, 8 pulled.
- **Each trade's return is set by the pool's depth.** Nobody trades between our buy and the launcher's, so the return is the price impact
  of its 0.05 ETH buy on the mint's L, and that L is known at the mint, before we buy:
  - L 3.681e22: +7.4% (24 h: 4 launches);
  - L 1.227e22: +22.8% (3 launches);
  - a 0.001 buy: +0.1%.

  The census's +66% came from shallower pools. Our $15 round trip around a 0.05 buy (V3Sim) makes +624% at L 3.68e20 (40 census
  launches), +46% at 6.27e21 (15) and +81% at 3.68e21 (6). In 48 h these tiers appeared once: a 3.68e21 launch that never bought. The
  census's main tier was 1.227e22 (245 launches, +23%).
- **(b) adds nothing to the return:** (b) and (a) are identical trade by trade, because the price does not move before the own buy. Its
  only gain would be less exposure, and its timing cannot be predicted to 2 blocks: after the dEaD transfer the gap is 85..129 blocks
  (n 4), and from the launch it is +138..+184. A fixed entry at the mint +106 catches all 4 late launches, but n 4 cannot validate it.
- **(c) +200's extra return** comes from the 7702 followers in 2 pools. In the 0.001 regime, fixed exits are pulled (44 of 50).

## Reaction (s07)
- **Fresh 50 h:** no case. No outsider bought before the launcher's own buy in any of the 70 launches.
- **Census, Oct 4-11:** 9 of 477 launches had an outsider buy before the own buy.
  - **6 of 9: the launcher still bought** 0.05 at +22..+28. Its pulls came at +69..+304, against +64..+288 in the same wallets'
    launches without an outsider, so not sooner.
  - **3 of 9: it did not buy,** and pulled at +41/+97/+120. All 3 are wallet 0x27041c7a on Oct 9 at 10:48-10:49. Just before, sniper
    0x81586f00 had run exactly rule (a) on that wallet twice: 0.00201 ETH bought at the mint +1, sold for 0.00296 one block after the 0.05 buy
    (+47%). The wallet's next two launches had no sniper, and it still made no 0.05 buy: one was pulled at +22, the other got 4×0.01 buys
    and was pulled at +259.

  So the operator answered being sniped twice by **dropping its 0.05 buy across launches,** not pool by pool. This is n = 1 episode.

  Whether the new ~9 s wait before the buy is a sniper check cannot be told: none of the 4 late launches had a buyer ahead.

## Gate for a $5 probe (judged on a rerun of s01-s06 at about 13:00 UTC)
1. At least 4 line launches in the 6 h (fee 100, 13ead562 to 0x73991a25, the one-sided [-887272, 204200] mint by the launch wallet).
2. The own first buy is 0.05 ETH (shape as above) in ≥80% of them, with no launch lacking an own buy. No return of the 0.001 regime.
3. Every own buy lands ≥10 blocks after the mint and ≤+190 after the launch. Report the transfer→buy gap.
4. No pull at or before the own buy + 3 (0 of 70 now).
5. No outsider buy between the mint and the own buy. If one appears, the launcher must still buy 0.05 in that pool, and in that wallet's
   next launch.
6. Rule (a) replayed on those launches: mean ≥ +5% at $5, win ≥ 0.9, 0 pulled.

While the probe runs, halt on any of:
- a probe pool where the launcher does not buy by +200, or pulls first;
- two 0.001 own buys in a row;
- a failed sell.

At $5 a trade nets +$0.35 at the 3.68e22 tier and +$1.12 at 1.227e22, so the probe buys information, not profit.

## What the engine would need
- **Carries over:**
  - launch-rule recognition by call shape plus code-hash prefix: 13ead562/132 B/value 0, prefix 0a493d1a. The target is one fixed
    address, so the code is read once.
  - the V3 CREATE2 pool and its price, straight from the call's arguments (the 132-B layout `decode_launch_v3` already parses).
  - the 356-B MintParams parse and `v3_liquidity`: the same layout `decode_launch_v3` reads inside the 836-B multicall.
  - SwapRouter02's `exactInputSingle` parse, the price copy, the pull test (`decreaseLiquidity` 0c49ccbe of the position id at the
    PositionManager) and dry_ret.
- **New:**
  - **Fire on the mint, not on a fixed offset.** The mint arrives as a later standalone tx (value 0 to 0x73991a25, 88316456, 356 B,
    matching the pool's tokens and fee), and the buy goes at the mint + 2. A fixed `buy_at` breaks because the mint moved from +5..+8 to
    +28..+32. The launch receipt holds no Mint, so `pool_from_receipt_v3`/`launch_fingerprint` would see 0 mints and never trade.
  - **Take the position id from the mint's receipt** (IncreaseLiquidity).
  - **A trigger-based exit.** The trigger is the own buy: to 0xcaf681a6, 04e45aaf, 228 B, tokenOut the token, fee 100, value = amountIn
    ≥0.045 ETH, minOut 0, recipient = the mint's recipient. That recipient check means no sender recovery is needed (`parse_tx` has
    none). The sell goes at the own buy + 1, capped at the launch + 200. The launch-rule path has no exit clock; it would reuse the
    crowd line's (`on_v3_buy`, `exit_after_blocks` 1).
  - **Mirrored launches:** `front_mismatch` refuses WETH-as-token1 launches (1 of 8 in 24 h).
  - **A live route to V3:** the dry run works today, but no route to a V3 pool exists, and that route is needed for any probe.

## Limits
- The 24 h sample is n 8 and the late timing is n 4. 0 pulls before the own buy in 70 launches leaves a 95% upper bound of about 4%.
- The rate is the main unknown: 1 launch in the 19 h before 02:06, then 7 in 5 h.
- A replay cannot show a reaction to our own buy, and reverted txs are not in the data.
- The $/day figures assume every launch is caught at the mint + 2 and sold one block after the own buy.
