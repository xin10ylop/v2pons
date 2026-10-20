# REPORT_C1R: does the C-1 operator react to an outside buy? (Oct 12, 2026)

Verdict: **KEEP THE HALT** (the analyst and both skeptics agree). Read-only research on the public RPC; no engine change.

## Analyst

Verdict: KEEP THE HALT. The C-1 operator does not pull about 9 blocks after any non-dust buy, as the volume bot does. It reacts more slowly, against outsiders who are still holding: it stops buying and pulls 36-175 blocks (4-18 s) after their buy.

That reaction hit our relay:
- 4 of 5 fills were pulled 36, 84, 97 and 115 blocks after our buy.
- Against the 147 pools with no outside holder: 2/147 pulled by T+120, Fisher p 3.5e-6.
- In all 4 of those pools the router never bought after T+62 (6/147 elsewhere).
- A stranger holder got the same treatment: 0x5b0320fb, 6 of 6 pools pulled 65-174 blocks after its buy. So the reaction is position-based, and a fresh relay address probably would not help.
- Pulls inside the hold for holders of our size: 2/20 (10%, Wilson 2.8-30%); ours alone 1/5. Break-even is 9.9% at +11% winners, 3.4% at our realized +3.6%.
- Counterpoint, not enough to lift: in the last 6 h (78 launches) the only non-dust holder was the recurring bot 0xbd9dc5f6 (0.0013-0.0018 ETH at T+15..51). Its 6 pools were not pulled by T+200 and the router kept buying. No stranger bought in (T, T+10] in the last 23 h, so the current burst has not been tested on a T+2 buy at our size.

DATA: blocks 85,436,881 to 86,692,583 (9.69 blocks/s).
- 188 C-1 launches: fee 100, tick spacing 1, ETH pair, a 2,276-byte value-0 PositionManager call, the line's sqrtP, no hooks.
- 169 pools have T, the first swap whose transaction goes to router 0xd6d35b56; 1,472 router EOAs.
- 185 pools were pulled, every one by the pool's launch wallet through the PositionManager.
- 84,731 swaps and 373 ModifyLiquidity events. Every swap in [launch, min(pull, launch+3000)] and in [pull-300, pull] is attributed: 14,650 transactions, none unattributed in any window measured.
- About 1,110 RPC POSTs, 0.5 s apart, 8 responses with HTTP 429. The node keeps no historical state, so our nonces were found by scanning blocks.

Buyers after T and before the pull:
- Router: 8,700 buys, 1,497 ETH, 164 pools.
- 25 recurring wallets: 779 buys, 1.19 ETH, 166 pools.
- 47 one-off wallets: 74 buys, 0.61 ETH, 52 pools.
- Ours: 5 buys.

Recurring wallets of note:
- Before T: 0xe71a69f4 (2e-6, sentinel), 0xd2b94182, 0x8dc68003, 0x5e6ec144.
- 0x97ac054b: 0.00019 at T+2..106 in 155 pools.
- 0xbd9dc5f6: 0.0003-0.0018 at T+15..150, sells 300 blocks later.
- 0x89b1da45: 0.008-0.03 at T+160..300.
- 0xf4a0048b: 0.03-0.06, sells after 30 blocks.
- 0x5b0320fb: 0.0025-0.005 at T-23..T+26, never sells.

(1) Window (T, T+10]:
- Strangers: 3 pools, all 0xc2101da8 (0.00995 at T+3, sold after 56-80 blocks). 0/0/0 pulled within 62/100/200; lags 7,292, 31,548 and 49,859. The router waited for it to sell in 2 of 3.
- 98 controls: 0/3/14 pulled by T+62/100/200.
- Ours: 1/3/4 of 5; lags 36, 84, 97, 115, 65,223.

(2) Any offset, first non-dust outside buy per pool:
- All non-dust: 0/108 within 62 (Wilson upper 3.4%), 21 within 100, 41 within 200; lags p10/25/50 80/124/392. These are mostly late recurring buyers just before the normal pull at T+250..400.
- Per buy: 3/137 followed by a pull within 62, all late (T+255..474).

Holders at T+62 (pulled by T+62/120/200):

| Group | Result |
|---|---|
| Outside holders | 1/3/6 of 15 |
| Ours | 1/4/4 of 5 |
| Rest | 0/2/12 of 147 |

Fisher p at T+120: holders 0.006, ours 3.5e-6.

(3) Our trades: see our_trades. Gross returns from chain prices reproduce the box log exactly.

(4) 6-hour slices (rest / holders / ours, pulled by T+62/120/200 then pool count; the last two columns are for rest pools):

| Slice (UTC) | Rest | Holders | Ours | Router ETH in hold, median | Gross mean |
|---|---|---|---|---|---|
| Oct 11 01-07 | 0/0/2 of 17 | 0/0/0 of 2 | – | 0.079 | +23% |
| Oct 11 07-13 | 0/0/0 of 16 | – | – | 0.477 | +19% |
| Oct 11 13-19 | 0/1/4 of 31 | 0/2/3 of 3 | – | 0.108 | +13.5% |
| Oct 11 19 to Oct 12 01 | 0/0/0 of 8 | 1/1/3 of 4 | 0/2/2 of 3 | 0.013 | +4.6% |
| Oct 12 01-07 | 0/0/1 of 9 | – | 1/2/2 of 2 | 0.420 | +12.6% |
| Oct 12 07-13 | 0/1/5 of 68 | 0/0/0 of 6 | – | 0.401 | +11.6% |

- Last 3 h: 55 pools, +13.8% mean, +10.6% median, 53 up, 0 pulled in the hold.
- Last 6 h, pull minus T: p5 187, p50 682.

(5) Break-even: see break_even. The reaction lag (median about 97 blocks) sits right on top of the 60-block hold. A slightly faster reaction or a slower sell turns our near-misses into -100% trades.

Notes:
- The 12:52 watch's "others ≤ 0.06 ETH" is confirmed. Every early outside buyer in the current burst is a recurring dust or near-dust bot.
- The relay's 3 reverted buys show the operator ignores attempts that leave no position.

Nothing was committed and the engine was not touched.

## Our 8 live trades

On chain there were 5 fills and 3 reverted buys. Gross returns from pool prices match the box log.

| # | Launch (UTC) | Pool | T | Our buy | Sell | Pull | Router ETH bought in our hold | Gross |
|---|---|---|---|---|---|---|---|---|
| 1 | Oct 11 20:58:49 | 0x5ec68315 | +77 | +79 (T+2) | buy+61 | buy+97 (T+99) | 0.20 | +4.1% |
| 2 | 20:59:59 | 0x35869115 | +277 | reverted at T+7 (21:00:28) | – | T+406 | – | – |
| 3 | 21:01:47 | 0xd6180333 | +41 | T+2 | buy+62 | buy+115 | 0.332 | +6.7% |
| 4 | 21:02:38 | 0x6d80b816 | +33 | T+2 | buy+62 | buy+65,223 | 0 | 0.0% |
| 5 | 22:16:34 | 0xd4654e14 | +118 | reverted at T+2 | – | T+56,247 | – | – |
| 6 | 23:54:58 | 0x266d00f1 | +103 | reverted at T+2 (23:55:08) | – | T+67,167 | – | – |
| 7 | Oct 12 01:15:58 | 0x0e4cc1d8 | +61 | T+2 | buy+62 | buy+84 | 0.174 | +3.5% |
| 8 | 01:18:11 | 0xb47b706f | +155 | T+2 | reverted at buy+62 | buy+36 (T+38) | 1.008 (3 buys) | -100% |

- Trade 6 is not in the box-log list. The box-log entries at 21:00:34 and 22:16:53 are the reverted sell attempts that followed reverted buys.
- In pools 1, 3, 7 and 8 the router never bought after T+62. The launch wallet pulled 9-68 blocks after the router's last buy.
- In pool 4 the router paused through our hold and resumed at buy+76, after we sold. It then bought 13.7 ETH and the pool lived.
- The other outside buyers in our pools were all dust: recurring wallets, plus 0xba0f83ea at 0.000195 ETH.
- The reverted buys (~60k gas, no position) drew no early pull. That fits a reaction to a held position, not to a transaction.

## Break-even

At $5 a trade, a pull costs $5 and a +11% winner earns $0.55, so the break-even pull rate is 0.55/5.55 = 9.9%. With our realized winners (mean +3.6% on the 4 that survived) it is 3.4%; at +7% it is 6.5%.

Measured rate of a pull inside the hold after an outside buy of our size:

| Group | Pulled inside the hold | Rate | Wilson 95% | Exact one-sided upper |
|---|---|---|---|---|
| Strangers buying in (T, T+10] | 0/3 | 0% | 0-56% | 63% |
| Stranger holders at T+62 | 1/15 | 6.7% | 1.2-30% | – |
| Our relay | 1/5 | 20% | 3.6-62% | 66% |
| All holders including ours | 2/20 | 10% | 2.8-30% | – |

- All holders, pulled within 120 blocks: 7/20 (35%).
- The 2/20 is not clearly under 5%. It sits at break-even for +11% winners and well above it for the +3.6% we actually got.
- The reaction targets holders: p = 3.5e-6 for ours vs the rest by T+120.
- It lands 36-175 blocks after the buy. Our 3 surviving pulled pools were pulled 22-53 blocks after our sell.

## Pull after an outside buy

This covers 36 h (Oct 11 01:00 to Oct 12 13:00 UTC): 188 C-1 launches, 169 with a router trigger T, 185 pulled by the head. Every swap in the windows measured is matched to its transaction.

(1) Our window, a non-dust outside buy in (T, T+10]:
- Strangers: only 3 pools in 36 h, all one wallet, 0xc2101da8. It bought 0.00995 ETH at T+3 (Oct 11 05:57, 06:12, 07:15) and sold 56-80 blocks later.
  - Pulled within 62 / 100 / 200 blocks of its buy: 0 / 0 / 0. The pulls came 7,292, 31,548 and 49,859 blocks later.
  - In 2 of the 3 the router held off buying until it had sold.
- Control pools (98, no outside buy of 0.0001 ETH or more in the window): pulled by T+62 0, by T+100 3, by T+200 14.
- Our relay in the same window (5 fills at T+2): 1 pulled within 62 blocks, 3 within 100, 4 within 200. Lags: 36, 84, 97, 115, and 65,223 for the pool that survived.

(2) Outside buys at any offset after T (first non-dust buy per pool, up to launch+3000):
- All non-dust sizes (108 pools): 0 pulled within 62 (Wilson upper 3.4%), 21 within 100, 41 within 200. Lags p10/25/50: 80/124/392.
- Our size, 0.001-0.0105 ETH (86 pools): 0 within 62 (exact upper 3.4%), 9 within 100, 25 within 200.
- These are mostly late buys (T+160 to T+1500) by recurring wallets, in pools whose normal pull is at T+250 to T+400. They say little about a T+2 entry.
- Per buy: 3 of 137 non-dust buys were followed by a pull within 62 blocks, all late (T+255 to T+474), just before the normal pull.

The test that matters, an outsider still holding at T+62 (non-dust buy anywhere from launch to T+62, not sold):

| Group | Pools | Pulled by T+62 | By T+120 | By T+200 |
|---|---|---|---|---|
| Outside holders | 15 | 1 | 3 | 6 |
| Ours | 5 | 1 | 4 | 4 |
| Rest | 147 | 0 | 2 | 12 |

- Fisher p at T+120: holders vs rest 0.006, ours vs rest 3.5e-6.
- 0x5b0320fb, a stranger holding 0.0025-0.005 ETH, was pulled 65-174 blocks after its buy in 6 of 6 pools.
- The router never bought after T+62 in 4 of 5 of ours, 2 of 15 holder pools and 6 of 147 others.
- So the reaction targets whoever is holding. It is slower than the volume bot's ~9 blocks: lags run 36 to 175 blocks, median about 97.

(4) 6-hour slices (pulled by T+62 / T+120 / T+200, then the pool count):

| Slice (UTC) | Rest | Holders | Ours |
|---|---|---|---|
| Oct 11 01-07 | 0/0/2 of 17 | 0/0/0 of 2 | – |
| Oct 11 07-13 | 0/0/0 of 16 | – | – |
| Oct 11 13-19 | 0/1/4 of 31 | 0/2/3 of 3 | – |
| Oct 11 19 to Oct 12 01 | 0/0/0 of 8 | 1/1/3 of 4 | 0/2/2 of 3 |
| Oct 12 01-07 | 0/0/1 of 9 | – | 1/2/2 of 2 |
| Last 6 h | 0/1/5 of 68 | 0/0/0 of 6 | – |

- All 6 holder pools in the last 6 h are the recurring bot 0xbd9dc5f6 (0.0013-0.0018 ETH at T+15..51). None was pulled and the router kept buying.
- No stranger bought in (T, T+10] in the last 23 h, so the current burst is untested at our size and timing.
- Last 6 h, pull minus T: p5 187, p50 682.

## Skeptic 1: the last 8 hours (Oct 12 05:52-14:07 UTC)

Refuted: False. Verdict agrees: True.

### Measured

All of this was measured with my own code, using only the public RPC at 0.5 s pacing. Scripts and JSON are in /tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/s1/ (s01-s13, p0*/q0*/n0*). I sent about 1,600 POSTs and got about 120 HTTP 429s (handled by backoff). No files in the repo were edited.

DATA. The slice is the last 8 h: 05:52-13:52 UTC Oct 12, blocks 86,441,903-86,722,384, extended to 14:07.
- 98 C-1 launches: fee 100, ts 1, no hooks, the line's sqrtP, PosM multicall 0xac9650d8 of 2,276 bytes, value 0, add liquidity = 100000088127620690885293.
- 94 have T (selector e6cb474f), and every pull was made by the pool's launch wallet through PosM.
- All 3,400 swaps in [L, L+1500] are matched to their transaction.

(1) Outside buy of 0.001-0.0105 ETH at T+1..T+10:
- With such a buy: 0 pools. Nobody bought that size in that window, so the test cannot be run.
- Without: 0/94 pulled by T+64.
- Widening to T+1..T+62 gives 12 pools, all 0xbd9dc5f6: 0 pulled within 62 blocks of its buy, 1 by T+120, 1 by T+200.
- Same-age check for outside buys of our size at any offset: 5 pulled within 62 blocks of the buy, against 4.35 expected from all pools alive at the same age.
- No pool in the slice was pulled by T+64.
- The rule (price after T+2 to price at T+64) with no reaction: n 94, gross mean +9.0%, median +7.9%, 87 up.

(2) Classification:
- bd9dc5f6 is a real outsider. Its first-ever token receipt was Oct 11 20:59:01, seconds after our first live C-1 buy. It was funded at 20:52 with 0.0300 ETH by 0x344daadde, a wallet with nonce about 819k that attaches calldata (0x16af6b29) to a plain ETH transfer, which looks like a bridge solver.
- The operator funds its launch wallets in a chain: the previous launch wallet sends about 1.2 ETH through contract 0xf341c935 to the next one. bd9dc5f6 is not in that chain.
- The other wallets:
  - 0x97ac054b: 0.0002 ETH dust, sells within 62 blocks.
  - 0x3155c72d: 0.00117 ETH, never sells, buys at T+91 or later.
  - 0x89b1da45: 0.008-0.03 ETH at T+144..336, never sells, nonce 16 before its first C-1 buy, no funding seen in the 8,000 blocks before.
  - 0x117ca425: uses its own bot contract, nonce 43.
  - None is linked to the operator. The analyst's labels hold.

(3) The reaction in the slice, which ran against bd9dc5f6:
- Pools where it bought were pulled by T+200 in 9/40, against 1/54 without it (Fisher one-sided p 0.0017). It does not pick weaker pools: router ETH in [T, T+20] is 0.24 vs 0.28, with the same T and the same first-buy size.
- Before 13:15: 4/33 vs 1/51. Its 11 positions of 0.001 ETH or more were not pulled early, matching the analyst through 13:00.
- 13:15-13:38: 5/7 vs 0/3. The pulls came at T+109..190, 45, 54, 72, 91 and 116 blocks after its buy, all while it still held. 2 of the 7 fell within 62 blocks of its buy.
- In each of these pools the router stopped early (3-5 buys) and the pull came 30-60 blocks after its last buy.
- Only one launch came after 13:38 (at 14:01), without bd9dc5f6, and it ran normally. Too little to test the pattern out of sample.

(4) Our trades, re-fetched for Oct 11 19:00 to Oct 12 03:00 (22 launches): 5 fills.
- Pulls came 97, 115, 84 and 36 blocks after our buy, at T+99/117/86/38. The fifth pool lived to T+65,225.
- The other pools in that window were pulled at T+19, 156, 176, 406, 494, 588, 649, 2,905 and later.
- Pulled by T+120: ours 4/5, the rest 1/15 (p 0.0049). The one early pull in the rest had a single router buy at T.
- The router never bought after T+62 in 4/5 of ours and 1/15 of the rest.

### Reasons

I could not refute KEEP THE HALT on the most recent 8 hours.

The direct test has no cases: no stranger bought 0.001-0.01 ETH at T+1..T+10. So my slice cannot show the risk directly. The 0/94 pulls by T+64 and the +9% gross return describe pools in which nobody held an early position of our size.

The strongest case against the halt was bd9dc5f6. It is a genuine outsider: bridge-funded, not in the operator's launch-wallet funding chain. Its 0.0013-0.0018 ETH positions at T+14..56 were not pulled early through 13:11. That case falls apart over the whole slice:
- Pools where it bought were pulled by T+200 far more often than the rest (9/40 vs 1/54, p 0.0017).
- It does not pick weaker pools to begin with.
- From 13:15, 5 of its 7 pools were pulled at T+109..190, 45-116 blocks after its buy, while it held. 2 of 7 came within 62 blocks of its buy.
- The pattern matches our own pools: the router stops after a few buys and the pull follows 30-60 blocks later.

So the reaction to whoever holds is present in the current burst, against a holder of our size with a different address and route. That backs the analyst's "position-based, a fresh relay address probably would not help".

Our own fills also look like a reaction: 4/5 pulled 36-115 blocks after our buy, against 1/15 same-window pools by T+120.

How much reaches inside our 62-block hold:
- bd9dc5f6, whole slice: 2 of its 40 positions (5%) were pulled within 62 blocks of its buy.
- bd9dc5f6, since 13:15: 2/7.
- Our relay: 1/5.
Break-even is about 8% at +9% winners. With a reaction lag of 36-116 blocks and a T+2 entry, the inside-hold pull rate is probably above break-even.

Caveats:
- The 13:15+ cluster is small (p 0.083 on its own), and only one launch came after it.
- Same-age checks of outside buys at later offsets show no extra pulls within 62 blocks (5 vs 4.35).
- The analyst's "holders 0/0/0 of 6 in the last 6 h, router kept buying" was right up to 13:00 but is out of date as of 13:15-13:38.

## Skeptic 2: Oct 11 12:00 to Oct 12 04:00 UTC

Refuted: False. Verdict agrees: True.

### Measured

Slice: Oct 11 12:00 to Oct 12 04:00 UTC, blocks 85,816,442 to 86,376,497. I re-fetched everything myself and ran my own scripts. The analyst's files were used only to look up our tx hashes.

Data:
- About 1,330 POSTs to rpc.mainnet.chain.robinhood.com, at least 0.6 s apart, backing off on HTTP 429. Read methods only.
- 60 C-1 launches: 2,276-byte value-0 PositionManager call, fee 100, tick spacing 1, the line's sqrtP and liquidity, no hooks. Each came from a different launch wallet.
- All 60 were pulled by their own launch wallet through the PositionManager. 57 had a router trigger T.
- 36,712 swaps up to the pull. All 5,389 transactions in [launch, min(pull, launch+3000)] and [pull-300, pull] were fetched and classified.
- 910 router EOAs. None of the 46 outside wallets overlaps a router EOA or a launch wallet.

(1) Outside buy of 0.001 to 0.0105 ETH at T+1..T+10:
- No stranger made one anywhere in the slice. 22 pools had only dust buys (0.00017-0.0005 ETH, from 0x97ac054b, 0x8dc68003, 0x5e6ec144, 0x4d42774f).
- Our relay is the only "with" group: 5 fills.
  - 1 pulled inside the hold (the 01:18 trade, 36 blocks after our buy): 1/5, Wilson 3.6-62%.
  - Lags from our buy: 97, 115, 84, 36, 65,223. So 4/5 were pulled within 115 blocks.
- Without such a buy (52 pools, not ours): 2 pulled by T+64, 3.8%.
  - 0x91620507 at T+63 and 0xcf1d880b at T+19. Both already had a non-dust outsider holding from before T: 0x5b0320fb with 0.005 ETH at T-23, and 0x5373fb35 with 0.002 ETH at T-140.
  - Pools with no non-dust outside holder at all: 0/45 by T+64 (one-sided 95% upper 6.4%), 1/45 by T+120, 5/45 by T+200.
- The analyst counts "inside the hold" as pulled by T+62. Our sell actually lands at about T+64, so 0x91620507's pull at T+63 falls inside our real hold.

(2) Holders (non-dust outsider holding at T+62) against the rest:
- Ours pulled by T+120: 4/5 against rest 1/45 (Fisher p 1e-4).
- Against rest pools where, as in our fills, the router bought only once by T+2: 1/32 (p 4e-4).
- Holder pools: 2/7 by T+64, 6/7 by T+200, against rest 0/45 and 5/45.
- Short type (the router never sells before the pull):
  - Holder pools: 8/8, counting one pool with no T.
  - Ours: 4/5. Rest: 11/47. Fisher, holders plus ours against rest: p 1e-5.

(3) Our trades against the normal pull time:
- The rest pull at a median of about T+1,900. Short-type rest pools pull at T+113..406.
- Measured from launch:
  - Ours pulled at launch+147..193.
  - Holder pools pulled at launch+133..246 (one at 526).
  - Short-type rest pools pulled at launch+201..373 (then 683, 2,402).
- In the 4 pools that were pulled, the router bought 0.17-1.0 ETH during our hold, stopped at T+29..49, and pulled 9-68 blocks later.
- In 0x6d80b816 the router paused from T+0 to T+78, which covers our hold (T+2 to T+64). It resumed 14 blocks after our sell, and the pool lived 65k blocks.
- In 3 of the 4 pulled pools the pull came 22-53 blocks after we had sold.

(4) Rule forward test on the slice (entry at the last swap at or before T+2, exit at the last swap at or before T+64, -100% if pulled by T+64):
- Pools without us: mean +2.3% gross, median +2.1%.
- All 57 pools: mean +0.6%. Survivors: mean +6.2%.
- By 4-hour block: Oct 11 20-24 h, mean -5.0%; Oct 12 00-04 h, mean -5.3%.
- Pulls inside the hold: 3/57 (5.3%). Break-even is about 5.8% at +6.2% winners, so the rule is roughly break-even before costs even if there is no reaction at all.

Classification:
- 0x5b0320fb (6 of the 8 holder pools):
  - Funded at 13:19 by 0xf316f91a, a 5-nonce EOA that holds 0.036 ETH and has no C-1 role. 0x5b0320fb itself had sent it 0.002 at nonce 0.
  - It has made 14 transactions in all, holds 4e-6 ETH and never sold. It lost all 6 positions to the pulls.
  - It looks like a retail stranger, not an operator decoy.
- 0xbd9dc5f6:
  - Funded at 20:52 by 0x344daadd, an EOA at nonce 818,388 that looks like a service hot wallet.
  - Its first C-1 trade was at 20:59, in our first pool. No tie to the operator.
- The dust bots 0xe71a69f4 (in 60/60 pools, at launch+2..3) and 0x8dc68003 (in 60/60 pools, 0.0004 ETH, never sells) could be the operator's own. They are below the 0.001 ETH line and change no non-dust result.

### Reasons

I could not refute the verdict on this slice; my own re-measurement supports KEEP THE HALT.

1. The direct test can't be run on strangers here. No stranger bought 0.001-0.01 ETH at T+1..10 in these 16 h, and the analyst's 3 such buys were Oct 11 05:57-07:15, outside my slice. The only fills of that kind are our relay's 5, and those look like a reaction:
   - 4/5 were pulled 36-115 blocks after our buy, 1 of them inside the hold.
   - Comparable pools with no outside holder: 1/32 or 1/45 pulled by T+120.

2. My checks point the same way:
   - Strata measured at T+2 do not explain it. Restricting to pools where the router bought only once by T+2, the condition under which our buys filled, still gives 1/32.
   - The holder pattern holds: every pool with a non-dust outside holder was short-type.
   - Pool 0x6d80b816: the router paused exactly through our hold and resumed after our sell.
   - On funding, the main stranger holder (0x5b0320fb) and the later bot (0xbd9dc5f6) have no link to any launch wallet or router EOA I could find. The "stranger" label holds, so the holder evidence is not operator decoys.

3. Even ignoring any reaction, the slice does not pay. The rule's gross mean is +2.3% on pools without us and +0.6% with ours. 2 of the 52 pools without us were pulled inside the real hold, which ends at about T+64. That is at or above break-even for the winners this slice produced.

Caveats on the analyst's write-up (none changes the verdict):
- The holder evidence is not independent. On my slice it is mostly one wallet (0x5b0320fb, 6 of 8 pools) plus 0x5373fb35.
- Using T+62 instead of our real exit at about T+64 misses 0x91620507's pull at T+63.
- In 3 of the 4 pulled pools the pull came after we sold. Measured from launch, our pulls (launch+147..193) sit just before the normal short-type schedule (launch+201..373). So "pulls to capture whoever is holding" is too strong. A better description: an outside buy moves the pool onto the short path (the router never sells back), and the pull then comes on roughly the usual launch-relative schedule, somewhat earlier. That still puts a T+2 entry at high risk.
- One of the 3 pools where our buy reverted (0x35869115) was also short-type.

Scripts, outputs and funding scans are in /tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/s2/. No repo files were edited and nothing was committed.

## Files

- c01_launches.py, c01_launches.json, c01_meta.json: launches
- c02_events.py, c02_events.jsonl, c02_relay_swaps.json, c02_head.json: Swap and ModifyLiquidity logs, our relay's swaps
- c03_txs.py, c03_txs.jsonl, c03_txs.out: 14,650 attributed transactions
- c04_ours.py, c04_ours.json, c04_ours.out: our wallet's reverted transactions, found from the nonce gaps
- c05_build.py, c05_pools.json, c05_build.out: per-pool records and buyer classes
- c06_reaction.py, c06_reaction.out, c06_reaction.json, c06_cases.txt: measures 1 and 2, every non-dust outside buy listed
- c07_ours.py, c07_ours.out: our pools in detail
- c08_targeting.py, c08_targeting.out: ours vs other pools, Fisher tests
- c09_holders.py, c09_holders.out: early non-dust buyers, whether they held or sold
- c10_hold.py, c10_hold.out: returns, router buying in the hold, confidence intervals, break-even
- c11_exposure.py, c11_exposure.out: pools with an outsider holding at T+62
- c12_wallets.py, c12_wallets.out: per-wallet histories (0x5b0320fb, 0x5373fb35, 0xc2101da8, 0xbd9dc5f6, ours)
- c13_slices.py, c13_slices.out: 6-hour slices
- common.py, rpc.py (paced copy of W/rpc.py, read-only methods), rpc_log.jsonl

The raw caches (c02_events.jsonl, c03_txs.jsonl, c05_pools.json) are git-ignored; the scripts rebuild them from the public RPC.
