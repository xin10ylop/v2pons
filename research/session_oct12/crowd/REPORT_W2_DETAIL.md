# The V3 crowd check: analysts and skeptics (Oct 12)

## Analyst: replay

Replay of every v3crowd launch from Oct 10 12:00 to Oct 12 14:30 UTC (2.10 days, blocks 84,980,908-86,744,941). Read-only, public RPC only. Nothing edited in src/deploy/tests/docs and nothing committed by me; a "work in progress" commit by the orchestrating session picked up some of my files mid-run. No .md was written: my instructions forbid report files, so the report is here.

VERDICT. On paper the line passes REPORT_W's gate: 279 launches, mean +7.3% to +7.9% a trade after gas, no pull before +80, 133 launches a day. But it is a lottery that depends on a timing window the operator controls:
- The median trade loses: -0.05% at 0.0058 ETH, -0.6% at 0.0012.
- The top 10% of trades bring 77-83% of the gain. Without them the mean is +1.4% to +2.0%.
- One half hour (Oct 12 03:00-03:30, 5 trades of +110% to +214%, all through crowd contract 0x7feb3ecb) is worth about 3 points. Without it the mean is +4.3% to +4.9%, right at the gate.
- The edge needs a hold to about +80. Selling earlier: cap 70 gives +5.3%, cap 60 gives +3.3%. The operator's earliest pulls were at +86, +94, +95 and +98.
- Nothing in this replay (or in the box's dry run) ever put a position on chain. If this operator reacts as C-1's did (pull 36 blocks after our buy), a trade that holds to the cap becomes -100%. C-1's own router (0xd6d35b56, e6cb474f) bought in 2 of these pools before the crowd, 0.86 ETH in all, which links the two operators.
- Recommendation: do not size up on this replay. If anything goes live, make it a small probe (V3_SELL_CHECK=0, $5, its own halt file) whose first purpose is to see whether the crowd still comes and when the pull lands once we hold.

ETH PRICE. The USDG/WETH 0.01% pool (5,534 WETH) gives $2,515 per ETH, not ~$4,200, so the dollar stakes differ from the brief:
- the stakes asked for: 0.0012 / 0.0036 / 0.0058 ETH = $3.02 / $9.05 / $14.58;
- $5 / $10 / $15 = 0.0020 / 0.0040 / 0.0060 ETH;
- the box's ETH_USD is 2570.

METHOD.
- Launches: 289 have the shape (NPM 0x73991a25, multicall ac9650d8, 836 B, value 0, fee 100, WETH on one side). Each is from a fresh wallet. 279 have WETH as token0 and pass the engine's filters (front_mismatch). 10 have WETH as token1, which the engine skips. Seven (hi, L) variants.
- Exact V3 integer math: new port v3exact.py, covering TickMath, SqrtPriceMath, SwapMath, bitmap-word stepping and tick crossing. It reproduces 14,832 of 14,832 on-chain swaps of these pools exactly: amounts, sqrtP, L and tick. The only misses are 5 zero-amount swaps on pools already pulled.
- Cross-check: my "+2, lands +2" case is REPORT_W's rule, and it equals REPORT_W's forward test on all 29 shared launches to 4 decimals, with the same exit blocks.
- Rule:
  - our buy lands at the head of launch+1, +2 or +3;
  - the clock starts at the first buy the engine counts: a crowd call shape with an amount word of at least 0.005 ETH, or an ETH-value call carrying the token with at least 0.005 ETH, in a block at or after ours;
  - the sell is sent at that buy + 18, capped at launch+78, and lands 1 or 2 blocks later;
  - every swap in between is re-simulated by its input amount, so our own impact is included;
  - the first Burn with liquidity above 0 at or before the sell's block counts as -100%.
- Gas uses the relay figures in docs/RELAY_V3.md and HANDOFF 16.22: buy 260k + sell 175k at 0.0201 gwei = $0.022 a round trip. The L1 part is negligible (gasUsedForL1 under 1k); a pulled sell burns 500k.

RESULTS (net after gas, entry +2, sell landing +2):
| stake | mean | median | p10 / p25 / p75 / p90 | worst | top-10% share | mean without top 10% |
|---|---|---|---|---|---|---|
| 0.0012 | +7.32% | -0.62% | -0.75 / -0.69 / +3.84 / +17.54 | -0.75% | 83% | +1.40% |
| 0.0036 | +7.79% | -0.14% | -0.26 / -0.20 / +4.32 / +18.00 | -0.26% | 78% | +1.88% |
| 0.0058 | +7.87% | -0.05% | -0.17 / -0.11 / +4.40 / +18.08 | -0.17% | 77% | +1.97% |
- Gross (before gas): mean +8.03%, median +0.10%. The pool's own price move with no impact or fees: +8.07%.
- Entry +1 or +3 changes the mean by at most 0.04 point; almost nobody buys in +1..+3 except dust.
- A sell landing +1 instead of +2 is about 0.95 point lower (0.0058: +6.92%). Most of that is one trade, where the crowd bought 0.3 ETH at +79: +188% if our sell lands at +80, -0.12% at +79.

PULLS. 275 of 279 pools were pulled by the head, every one by its launch wallet through the NPM, removing 100% of the liquidity.
- Before +80: none. Earliest at +86, 94, 95 and 98.
- By +100: 4. By +150: 25. Median +682.
- Pulled before our sell: 0 in every configuration.

THE CROWD.
- Its first real buy appeared (by +1500) in 259 of 279 pools: median +92 (p10 +47, p90 +237), 101 by +78, median size 0.0495 ETH.
- It now rotates through 10 contracts (a28f468c, 80114879, fc7241d4, d26c8cfc, 7feb3ecb, af9d6fa0, 84021dc2, 71a7629f, 85ce7832, 80e49ed1), still using the same three call shapes.
- 82% of exits are at the cap; 18% come from the crowd's clock.

BUYERS BEFORE THE CROWD (to +200). Almost all are dust.
| contract | buys | pools | wallets | typical size | when |
|---|---|---|---|---|---|
| 0x65050a9b (with ETH value) | 524 | 204 | 38 | 0.00074 ETH | median +31 |
| SwapRouter02 | 221 | 221 | 1 (0x5718d14b) | 0.00028 | about +8 |
| 0x570759db | 148 | 148 | 1 (0x776e5a2a) | 0.00137 | +1 |
| 0xf0b7eaaf (with ETH value) | 65 | 53 | 6 | 0.0083 | – |
- Buys of 0.003 ETH or more before the crowd: 18, in 14 pools; only 1 of them in blocks up to +10.
- Pools with 0x776e5a2a's buy at +1 (a holder of about our $3 size): the crowd came by +80 just as often (0.38 vs 0.39). Pulls came earlier (12% vs 6% by +150; median +504 vs +784).

GATE (REPORT_W). Passes on all four counts over the window: n 279 (needs 100); mean +7.3% to +7.9% (needs +4%); no pull before +80; 133 a day (needs 120). But Oct 12 ran at only 113 a day, and the last 24 h had 121 launches.

PER DAY AND PER 6-H SLICE (0.0058):
| period | launches | mean | median / note |
|---|---|---|---|
| Oct 10, 12 h | 68 | +2.93% | -0.09% |
| Oct 11 | 143 | +5.09% | -0.02% |
| Oct 12, 14.5 h | 68 | +18.68% | +0.01%; +2.78% without its top 10% |
| 6-h slices, in order | 65 / 3 / 50 / 34 / 16 / 43 / 21 / 31 / 16 | +2.89 / +3.71 / +6.79 / +7.05 / +3.77 / +2.04 / +43.75 / +10.60 / +1.46% | – |

$ A DAY AFTER GAS. Assumes all 133 launches a day are traded, with no slot conflicts.
| stake | per trade | a day | without top 10% | median trade |
|---|---|---|---|---|
| $5 | $0.38 | $50.7 | $11.3 | -$0.017 |
| $10 | $0.79 | $104.2 | $25.4 | -$0.012 |
| $15 | $1.19 | $157.6 | $39.6 | -$0.007 |
With a +1 landing, about 12% less. A live V3 stake is capped at 0.004 ETH (about $10) unless V3_STAKE_CAP_ETH is raised.

THE BOX'S DRY +12.9%: its pricing is right; its window is the best stretch.
- I mimicked the engine's dry_ret. It prices at the send block, from a copy that takes the crowd's amount words and ETH-value buys, does not see sells, subtracts base_fee x 250k, and never checks pulls for a crowd family.
- Against my exact replay at the same price point (a sell landing +1), the mimic is within 0.1 point on 262 of 279 launches; mean difference -0.008 point; over all 279, +6.97% vs +6.92%.
- One exception: C-1's router bought 0.2 ETH at +58, which the engine cannot see (dry -0.11% vs exact +4.02%).
- The engine's trigger matcher reads none of the crowd's sells as buys.
- In the box's 24 h the chain had 121 launches: dry mimic +9.88%, exact +9.82% (landing +1) and +11.67% (landing +2).
- A random 95 of those 121 gives about +10.0% (90% range +6.9% to +12.1%) and never +12.9%. The last 90-100 launches before 14:23 (from about Oct 11 18:40-23:10, after v3crowd was added on Oct 11 evening) price at +11.4% to +12.4%. With slot skips on top, that fits +12.9%.
- From +12.9% to a real live result:
  - the window (2.1 days: +6.9% at the send-block price);
  - the landing, worth ±1 point, mostly from one trade;
  - gas: 250k assumed vs 435k, -0.06 point at 0.0058 and -0.26 at 0.0012;
  - pulls never counted by the dry (none fell before +86 in this data);
  - the reaction, which neither the dry run nor this replay can see.

### Numbers

Window Oct 10 12:00:00 to Oct 12 14:30:12 UTC = 2.10 days. 289 launches of the line's shape; 279 with WETH as token0 (traded); 10 with WETH as token1 (skipped by the engine). 132.6 launches/day (Oct 10 PM 136, Oct 11 143, Oct 12 113; last 24 h 121).
Simulator exact on 14,832/14,832 live swaps; equals REPORT_W's forward test on 29/29 launches.
ETH $2,515 (USDG/WETH 0.01% pool, 5,534 WETH). Base fee 0.0201 gwei. Gas 435k a round trip = $0.022.

Net after gas, entry +2, sell landing +2:
- 0.0012 ETH ($3.02): mean +7.32%, median -0.62%, p10 -0.75, p25 -0.69, p75 +3.84, p90 +17.54, worst -0.75%, best +214.4%, win 109/279, top-10% share 83%, bootstrap 90% interval [+4.89, +10.05].
- 0.0036 ETH ($9.05): mean +7.79%, median -0.14%, p10 -0.26, p25 -0.20, p75 +4.32, p90 +18.00, worst -0.26%, top-10% share 78%.
- 0.0058 ETH ($14.58): mean +7.87%, median -0.05%, p10 -0.17, p25 -0.11, p75 +4.40, p90 +18.08, worst -0.17%, win 121/279, top-10% share 77%, bootstrap [+5.45, +10.60].
- Entry +1 / +3 at 0.0058: +7.91% / +7.87%.
- Sell landing +1 at 0.0058: +6.92%.
- Gross mean +8.03% (median +0.10%); pool price move +8.07%.
- Mean without the top 10%: +1.40% / +1.88% / +1.97%. Without Oct 12 03:00-03:30: +4.30% / +4.78% / +4.87%.
- Cap 76 / 70 / 60 (landing +2): +6.54% / +5.30% / +3.30%. Cap 88: +9.00% (1 pull). Cap 98: +10.14% (2 pulls).

Pulls: 275/279 by the head, all by the launch wallet, 100% of the liquidity. Before +80: 0. Earliest +86, 94, 95, 98. By +100: 4. By +150: 25. Median +682. Pulled before our sell: 0 in every configuration.

Crowd's first real buy: 259/279 pools; median offset +92 (p10 47, p90 237); 101 by +78; median size 0.0495 ETH. Exits: at the cap 229, by the crowd's clock 50.

Per day at 0.0058: Oct 10 +2.93% (n 68), Oct 11 +5.09% (n 143), Oct 12 +18.68% (n 68). 6-h slices: +2.89, +3.71, +6.79, +7.05, +3.77, +2.04, +43.75, +10.60, +1.46%.

$/day after gas, all launches traded: $5 = $50.7 (without top 10%: $11.3); $10 = $104.2 ($25.4); $15 = $157.6 ($39.6). Median trade -$0.017 / -$0.012 / -$0.007.

Box comparison: engine-dry mimic +6.97% (all 279) vs exact landing +1 +6.92%. Box 24 h: mimic +9.88%, exact +9.82% / +11.67% (n 121). Random 95-subset: median +10.0%, 90% range +6.9 to +12.1%. Last 90 launches: +12.42%. The box reported +12.9%.

RPC: 779 POSTs, 6,733 items, about 19 minutes, 0.5 s pacing.

### Caveats

- No position was ever on chain, in this replay or in the box's dry run. The C-1 operator (live c1 halted today: pull 36 blocks after our buy) and the 3.0 bot both reacted to an outside holder. Here a pull before our sell is -100%, and the margin is 6 blocks (earliest pull +86 vs our landing +80). C-1's router bought in 2 of these pools, so the same operator may run both lines.
- The one natural test of a holder is weak. A single wallet (0x776e5a2a) buys about 0.0014 ETH at +1 in 144 pools. The crowd came just as often, but pulls came earlier (12% vs 6% by +150). Whether that wallet is an outsider is unknown.
- Timing assumptions:
  - our buy and our sell sit at the head of their blocks;
  - the cap's send is at launch+78 whatever the landing (the live engine's is buy block + send_after, lb+76+e);
  - results near the cap are sensitive: about 1 point of the mean rests on one trade whose crowd buy came at +79.
- Re-simulation keeps every later swap's input fixed. The crowd's min-out is 0, so its buys still go through behind ours; other buyers with a min-out could revert. Crowd sells are re-simulated by their token amount.
- Reverted calls (no Swap log) are not seen. The engine's feed sees them and could start its clock on one.
- $/day assumes every launch is traded. The single slot (v2.433 live, c1, the v3.0 dry watch at 588 trades a day) would skip about 5-10%.
- Gas comes from the relay's simulated and review figures. The V3 relay is not deployed, and no live V3 trade has run.
- ETH/USD comes from one on-chain pool ($2,515). The brief's ~$4,200 is wrong; the box uses 2,570.
- The box's 95-trade sample cannot be matched launch by launch without its logs. The window explanation (v3crowd armed from Oct 11 evening, plus slot skips) is an inference, not a proof.
- 20 pools never saw a crowd buy (by +1500). They are included: a sell at the cap for about -(fees + gas).
- The 10 WETH-token1 launches are excluded, as the engine skips them.
- A parallel session (crowd/reaction) is studying the operator's reaction. Its results should be read together with these.

### Files

All under /home/user/v2pons/research/session_oct12/crowd/replay/:
- Per-launch table: r12_launches.tsv. One row per launch: block and time, pool, token, WETH side, launch wallet, the crowd's first buy (offset, size, contract), the engine's trigger, every buyer before the crowd (offset:sender:to:size), the first Burn (offset, by the launch wallet), the exit, and gross/net at 0.0012/0.0036/0.0058 ETH for entries +1/+2/+3, landing +1, and the engine's dry.
- Statistics: r07_stats.out (every configuration, per day, per 6-h slice, pulls, crowd, buyers, gate, $/day, engine-dry comparison). r12_robust.out (bootstrap, without top trades, cap sensitivity, sell at the end of its block).
- Checks: r08_checks.out (vs REPORT_W's forward test 29/29; engine dry vs exact per launch; top 15 trades; box subset test). r10_box_window.out (the last-N launches vs the box's +12.9%). r09_trigger_word.out (the engine's matcher on crowd sells). r11_early_holders.out (pools with vs without early holders). r04_validate.out (simulator vs 14,832 swaps).
- Inputs: r05_gas_price.out / .json (base fee, crowd-buy receipts, ETH/USD). r01_launches.out / r01_launches.json (the 289 launches).
- Code: v3exact.py (exact V3 integer pool). r06_replay.py (the replay and the engine-dry mimic; output r06_rows.json). r01_launches.py, r02_events.py, r03_txs.py (data). common.py, rpc.py, v3dec.py.
- Raw caches (git-ignored): r02_events_cache.jsonl, r03_txs_cache.jsonl.

## Analyst: reaction

Short answer: yes, the v3crowd operator reacts to an outside holder, but slowly. With an outsider holding, it pulls the pool sooner, and nearly all of those pulls come just after our 80-block exit. Nothing measurable lands inside our hold today. The safety margin is only a few blocks, though, and it depends on our cap sell landing on time.

Scope: read-only, public RPC only (about 2,440 paced POSTs), no edits to src/, deploy/, tests/ or docs/, nothing committed. I did not write a .md report (my instructions say not to), so the report is this text.

Data: all 1,389 v3crowd launches from Oct 3 01:47 to Oct 12 13:44 UTC, 618 of them since Oct 8. Every swap from launch to the pull (or launch+3000) is attributed to its transaction. Crowd = the three crowd call shapes through any contract except the Universal Router. The pull is the pool's first Burn; all 1,089 pulls whose transaction I fetched came from the pool's own launch wallet. Our trade is modelled as the engine's rule: 0.00198 ETH (= $5 at $2,527, the on-chain USDG/WETH price, not $4,200) landing at +2, sold at the earlier of the crowd trigger +20 or +80, priced with analyst C's V3 replay. My pipeline matches REPORT_W's forward test on 29/29 first real buys and 28/28 pulls.

1) Outside buyers before the crowd are the norm, not the exception. 1,180 of 1,389 pools had a non-crowd wallet buy at least 0.0005 ETH before the crowd's first real buy; only 209 had none. Of 2,649 non-bot outsider positions, 2,391 still held when the crowd came (or at the pull) and 258 had sold. A recurring +1 bot (0x776e5a2a, via 0x570759db) buys about 0.001 ETH at +1 in 830 pools and holds, which makes it a natural experiment.

2) The crowd itself does not back off:
- Per pool-block, the crowd's first real buy comes slightly more often with a holder present: rate ratio 1.23 (95% CI 1.06-1.43); 1.24 (1.02-1.52) for holders of our size.
- With the +1 bot in the pool, the crowd's first 20-block wave is the same size (Mann-Whitney p 0.91), and the first real buy is as early or earlier.
- The crowd does not wait for outsiders to leave: after 258 outsider exits it came within 30 blocks less often than expected (observed/expected 0.60).
- No sign it learns: across 34 wallets that sold into the wave at a profit in 2 or more pools, their later pools still got the crowd by +78 at observed/expected 1.15.

3) What the operator does change is the pull:
- Before the crowd comes, the pull rate per pool-block is about 3x higher with a holder: 3.15 (1.82-5.46) for any holder, 3.77 (2.06-6.92) for holders of our size. Since Oct 8 it is 2.49 (1.00-6.20).
- With the +1 bot holding, the pull hazard is x1.42 (1.24-1.62), concentrated at +80..+200. Pools are pulled by +150 in 17.3% vs 10.1% (permutation p 0.0006), total crowd buying is down a third, and pulls come 80 rather than 115 blocks after the last real buy.
- It is not a fast reaction like the 3.0 bot's: pulls within 36 blocks of an outside buy are rarer than expected (observed/expected 0.47).
- The timing follows the launch, not the outsider's buy (slope 0.10). Where the crowd never came and an outsider held, pulls land around +86/+127/+141 (p10/median/p90).

4) Where it meets our trade. About 82-85% of our trades end at the +80 cap sell, because the crowd hasn't triggered by +60.
- Pools still waiting for the crowd at +78 with no outside holder (228): none pulled by +90, 0.9% by +100.
- With an outside holder of our size: 2.9% by +90, 4.4% by +100, 16.9% by +150.
- With a non-bot holder in since +1..+10 (our analog, 225 pools): 0.4% by +80, 0.9% by +83, 1.3% by +85, 3.1% by +90, 4.9% by +100.
- The quick pulls at +83..+90 were all Oct 3-7 (9 of 546). Since Oct 8 there were 0 of 298 by +90, 4 by +100, and 0 of 64 in the last 24 h.
- Pulls at or before our sell: 1 of 1,389 (Oct 4, pulled at +79, no crowd, five small holders) and 0 of 618 since Oct 8.

5) Who else fronts these launches:
- Only the +1 bot buys ahead of a +2 entry: it is at +1 in 778 pools and lands at +2 in 36. It raises our entry price by 0.05% (p90 0.08%), which is negligible. Within the observed window it lost about 94% (0.63 ETH in), though over the tokens' lifetime it got 0.89 ETH back for 0.82 ETH spent by selling rare long-lived winners. It is not funded from launch wallets.
- A set of SwapRouter02 sprayers buy 0.00015-0.00055 ETH at +4..+10 (0x9a128676, 0x1a16c51d, 0x5718d14b, 0x24a4c20f, 0x1a45411c). Their realized returns range from -100% to +9%.
- The trading-bot router 0x65050a9b: 43 wallets buying 0.0006-0.001 ETH at +10..+60, pooled +5.9%.
- 0xf0b7eaaf users, mostly unprofitable except 0x3029608e: 0.03 ETH positions, +14% pooled, +0.23 ETH.
- Nobody repeatedly buys at our size at +1..+2 and sells into the wave.

Conclusion: there is a reaction, and it is real (p below 1e-4 on several independent tests). It is slow and tied to the launch clock: when the crowd doesn't come, holder pools are pulled from about +83 on. It is not inside our 80-block hold: 1 pull at or before our sell in 1,389 pools, 0 in 618 since Oct 8, which bounds the rate at 0.3-0.5% at 95% confidence.

What the measured worst case costs a $5 trade:
- On-time sells (land at +80): at most about $0.02 expected per trade (upper bound), against a mean of +$0.35 per trade (+7.5%, median +0.14%; the top 10% of trades bring 76% of the gain).
- If the crowd never came while we hold: -$0.022 per trade (gas).
- If the cap sell lands late in a holder pool, using the Oct 3-12 rates: 3 blocks late about $0.04, 5 late about $0.06, 10 late about $0.13, 20 late about $0.21 per trade (95% upper bounds $0.12-$0.34).
- A single bad trade is -$5.02.

The two risks are the margin of about 3 blocks between our cap and the first reaction pulls, and the C-1 precedent: that operator sped up once a live wallet started extracting, which no dry result can show. Before going live: confirm the cap sell lands by +80, consider a 76-78 cap for extra margin (it costs some edge), and alert or halt on any pull at or before +90 in a pool where we hold.

### Numbers

DATA
- 1,389 launches, blocks 78,707,139 to 86,743,912 (head at 14:28 UTC Oct 12); 618 since Oct 8.
- Launches per day: 131-179 (70 on Oct 12 up to 13:44).
- 61 launches have WETH as token1.
- 1,381 pools pulled by the head; all 1,089 pulls with a known transaction came from the launch wallet.
- The crowd's first real buy (at least 0.005 ETH) came in 1,158 pools: p10/50/90 at +51/+91/+296; 183 by +60, 443 by +78.
- 88,123 swaps; 33,588 transactions fetched.
- RPC: 2,224 POSTs (35,710 items) plus 213 for r01; about 560 HTTP 429 responses, each retried after a back-off.
- ETH price $2,527 (USDG/WETH fee-100 pool), so $5 = 0.00198 ETH. Gas $0.022 per round trip.

THE RULE AT $5 (no reaction modelled)
- All pools: mean +7.53% (95% CI +6.44..+8.77), median +0.14%, top 10% bring 76%, $0.354 per trade.
- Since Oct 8: +7.34%, $0.345 per trade.
- Pulled at or before our sell: 1/1389 (exact 95% upper 0.34%); 0/618 since Oct 8 (upper 0.48%).
- 82-85% of trades sell at the +80 cap.

THE +1 BOT AS A NATURAL EXPERIMENT (814 pools with it, 575 without)
- Crowd by +78: 34.9% vs 32.9%.
- Crowd hazard: rate ratio 1.08 (0.95-1.23).
- First wave: Mann-Whitney p 0.91.
- Total buying: 1.22 vs 1.74 ETH (p 0.001).
- Buying span: 227 vs 489 blocks (p 0.0003).
- Pull after the last real buy: 80 vs 115 blocks (p 9e-9).
- Pulled by +150: 17.3% vs 10.1% (permutation p 0.0006).
- Pull hazard: 1.42 (1.24-1.62).
- Pulled at or before our sell: 0 vs 1.

HAZARDS (stratified by day x age band)
- Crowd, with any holder: 1.23 (1.06-1.43); non-bot holder 1.31; our size 1.24 (1.02-1.52).
- Pull before the crowd: 3.15 (1.82-5.46); non-bot 3.21; bot 4.35; our size 3.77 (2.06-6.92).
- Since Oct 8: crowd 1.15 (0.94-1.39); pull 2.49 (1.00-6.20).
- Same-age test, 2,214 non-bot outside buys, pulled before the crowd: within 36 blocks O/E 0.47 (0.24-0.82); within 78 O/E 1.28 (1.06-1.54); within 120 O/E 1.37.
- Early buyers (+1..+10): pulled within 78 blocks 4 vs 1.1 expected; crowd within 78 O/E 1.27.

CAP BRANCH (no crowd trigger by +60), pulled before the crowd
- No holder (n 228): 0 by +90, 0.9% by +100, 1.3% by +150.
- Non-bot holder (n 844): 1.1% by +90, 2.5% by +100, 10.8% by +150.
- Holder of our size (n 272): 2.9% (1.5-5.7) by +90, 4.4% (2.5-7.6) by +100, 16.9% by +150.
- Holder in since +1..+10 (n 225): 0.4% by +80, 0.9% by +83, 1.3% by +85, 3.1% by +90, 4.9% by +100.
- No crowd by +100, holder vs none, pulled by +150: 19-28% vs 1.9% (Fisher p 1e-9 to 1e-12); by +100: day-stratified CMH p about 0.07.
- By period, pulled by +90: Oct 3-7 9/546; Oct 8-12 0/298 (4 by +100); last 24 h 0/64.
- Timing follows the launch: slope 0.10.

PULL FLOOR
- Earliest pulls: +62, +79, +80, +83, +85, +85.
- Since Oct 8: 0 pulled by +80, 2 by +90, 13 by +100.

COST PER $5 TRADE (from the cap-branch rates)
- On-time sell: at most $0.017-0.024.
- 5 blocks late: about $0.06; 10 late: about $0.13; 20 late: about $0.21.
- Crowd never comes: -$0.022.

OTHER
- Outsiders who sold before the crowd: crowd within 30 blocks of their exit O/E 0.60.
- Repeat wave-sellers (34 wallets), in their later pools: crowd O/E 1.15; pulled by +150 O/E 1.44.
- Entry cost of the +1 bot to our +2 buy: 0.05% (p90 0.08%).

### Caveats

- Dry versus live: this is all observational. No position of ours has ever been held on this line. The closest analogs, outsiders of 0.0015 ETH or more buying at +1..+5, number only 11 pools since Oct 3. A live wallet that sells into the wave every time could be learned and targeted, as C-1 did after our trades; no dry result can show that.
- Regime change: the quick pulls at +83..+100 in holder pools were an Oct 3-7 pattern. Since Oct 8 none came by +90, but the sample is smaller (298 holder pools), and the operator's schedule is the whole margin.
- Margin: 82-85% of our trades sell at the +80 cap. The protection is about 3 blocks between our cap sell and the earliest reaction pulls (+83). Any slip in how fast the engine sends or lands the sell turns those pulls into -100% trades.
- Classification:
  - Outside wallets are identified by the transaction sender.
  - About 38k crowd swaps were classified from the Swap log without fetching the transaction (sells: the UR as sender and a crowd contract as recipient; later buys: a crowd EOA as recipient).
  - 17.5k later swaps stayed unclassified. These are buys more than 30 blocks after the crowd's first, which matter only for wave totals and a few wallets' realized returns.
  - Sells after +3000 are not seen.
- The +1 bot holds within the window but over the tokens' lifetime sells the rare long-lived winners (67 of 830 pools). Its funding does not trace to launch wallets, but it may still be special to the operator: the bot alone never drew a quick pull (0 of 115 by +100).
- Day-stratified tests weaken the +90/+100 results (CMH p 0.07-0.2). The +150 result and the hazard ratios stay strong.
- The line ran before Oct 3. I stopped the backward extension to Sep 28 after the box's disk filled (/ at 100%, ENOSPC) during the fetch; I repaired the transaction cache (one partial line removed). The public node returned many 429s and other agents were using it at the same time.
- Replay uses analyst C's float V3 simulator; the rule return ignores any reaction and any slip in landing time.

### Files

Directory: /home/user/v2pons/research/session_oct12/crowd/reaction/

Fetch scripts (read-only public RPC, paced; outputs in matching .out files):
- rpc.py — the polite client, 0.6 s between POSTs
- common.py, rlib.py — shared helpers and per-pool summaries
- r01_launches.py → r01_launches.json, r01_meta.json
- r02_events.py — pool events and burns (caches below)
- r03_txs.py — swap transactions (cache below)
- r04_build.py — per-pool build (cache below)
- r10_ethusd.py, r13_wallets.py, r18_bot_funding.py — ETH price, recurring wallets, the +1 bot's funding

Analysis scripts (local; outputs in matching .out files):
- r05_groups.py → r05_groups.out, r05_groups.json — groups, Fisher tests, pull floor, cap branch, closest analogs
- r06_hazard.py → r06_hazard.out, r06_hazard_oct8.out — hazards and same-age tests
- r07_sold.py → r07_sold.out, r07_cases.txt — outsiders who sold before the crowd
- r08_fronters.py → r08_fronters.out, r08_fronters.json
- r09_cost.py → r09_cost.out, r09_cost_oct8.out — cost per $5 trade
- r11_bot1_events.py, r14_bot_strat.py, r15_bot_wave.py, r17_bot_perm.py — the +1 bot experiment (logs only)
- r12_entry.py — entry cost of buyers ahead of us
- r16_early_pulls.py, r24_early_pull_cases.py — earliest pulls
- r20_validate_w.py — check against REPORT_W
- r23_extractors.py — repeat wave-sellers
- r25_data.py — data summary
- r21_pool.py — prints one pool's swaps

Runners: run_rest.sh (fetch), run_analysis.sh (all analyses). run_all.sh and r01_extend.py are the stopped backward extension; never run to completion.

Caches (git-ignored, *_cache.jsonl): r02_events_cache.jsonl, r02_burns_cache.jsonl, r03_txs_cache.jsonl, r04_pools_cache.jsonl. Rebuildable with run_rest.sh.

Key outputs to read first: r05_groups.out (sections b, e, g, h, i, j, l), r06_hazard.out, r09_cost.out, r11_bot1_events.out, r14_bot_strat.out, r17_bot_perm.out, r08_fronters.out, r23_extractors.out, r10_ethusd.out.

## Analyst: safety

## v3crowd: token safety and how the live trade would execute (read-only check, Oct 12, about 15:00 to 16:00 UTC)

**Verdict.**
- **The tokens are safe.** Every v3crowd token since Oct 10 is a plain ERC20. None has an owner, a tax, a lock or a trading switch, and outsiders really do sell them.
- **The live path works as built.** Our buy always lands ahead of the crowd. A launch that reverted (NoPool) would cost about $0.003.
- **The real risk is the operator.** Its pull or its reaction to us holding a position is the danger, and a dry run cannot show it. The family's pull halt is the guard.
- **Fix two settings before going live:**
  - The streak halt (`FRONT_NONBOT_HALT`, 8 on the box) would stop v3crowd about every 26 trades, roughly every 6 hours.
  - The stake. ETH is **$2,523.53**, not $4,200. So $5 is 0.002 ETH, and the box's 0.0058 ETH is capped to 0.004 ETH ($10.09).
- **The line has paused.** There has been no v3crowd launch since **13:44 UTC**, and none by 16:00 (2 h 16 min).

### 1. The tokens

**The launches.** There were 349 launches since Oct 10 00:00 (836-byte multicall to 0x73991a25, value 0, fee 100): 132 on Oct 10, 147 on Oct 11, 70 on Oct 12.
- 338 have WETH as token0. The engine arms all 338 (the token, alone, minted from the lowest tick up to the launch price).
- 11 have WETH as token1, which the engine skips.
- Each launch comes from its own fresh wallet. 346 of 349 wallets deploy the token, approve and launch at consecutive nonces. The other 3 sent a plain ETH transfer in between, which is not a reverted launch.
- Every pool was created in its own launch transaction: none was created beforehand.

**Three code templates, all plain ERC20s:**
- **A**: 1,764 bytes, code hash `0x19e3e2a65bec931da1e23da6c20891e1048da9c825ed1f713623b73b66aa00dc`, 340 tokens. This is REPORT_W's census template. It has only the 9 standard ERC20 functions.
- **B**: 5,048 bytes, an older OpenZeppelin ERC20 with increase/decreaseAllowance, 6 tokens. Each has its own hash, but only the compiler's metadata hash differs.
- **C (new)**: 3,854 bytes, code hash `0x5fcfacb98bd0b7c58b3388066cb6c31c255a3662d99b7df4eab8c89c5956505b`, 3 tokens (Oct 10 10:26, Oct 11 04:53 and 05:47). It is OpenZeppelin's ERC20Burnable: A's functions plus `burn` and `burnFrom`. Only a holder can burn, its own tokens or ones it is allowed to spend. That gives nobody any power over other holders.

**What none of the three has:**
- no owner, no mint after deployment;
- no pause, blacklist, max-transaction or max-wallet limit, and no trading switch;
- no external calls, `tx.origin`, timestamp, block number or `EXTCODESIZE`;
- no storage writes beyond balances, allowances and total supply.

Every token has 1e27 supply and 18 decimals, and nearly all of it goes into the pool at launch.

**Tested on the latest chain state** (eth_call with state overrides, nothing sent):
- An outsider's `transfer` into the pool, a `transferFrom` through SwapRouter02, and a transfer to a wallet all succeed: 349 of 349.
- The exact amount arrives every time (698 of 698), so there is no transfer tax and no burn on transfer.
- The relay's own buy then sell (FlipRelayV3's code) on the two pools still live costs exactly two 0.01% fees (−0.0200%). The buy uses about 235k gas and the sell about 152k as transactions.

**Outsiders' real sells** (from the reaction check's records):
- 1,317 sells in 298 of 349 pools: 104 sellers on template A, 42 on C, and 4 sells on B.
- Routes: the Universal Router, 0x65050a9b, 0xf0b7eaaf, C-1's router, SwapRouter02 and others.
- Sell timing after the launch: 10th percentile +121 blocks, median +350, 90th percentile +1,964.
- 350 outside positions were fully closed, with a realized median of +17.7%. That figure is biased upward: it only counts those who sold.
- A scan of every block from launch to +100 on the 10 latest pools found 40 transactions naming the token and **0 reverted**.
- 1,207 outside positions were still held when the pool was pulled, mostly the +1 dust bot. Outsiders lose to the pull, not to a lock.

### 2. Execution

**When the engine fires** (`src/flip_engine.py`):
- It arms the launch from the calldata alone, in the launch block's feed message. The pool address comes from CREATE2, with no RPC call.
- It fires at the end of that same block (`fire_at` 0). It does not arm a launch if the feed is more than 2.5 s behind.
- The trade is live only if the V3 relay was verified at start, the family says `dry_run:false`, `DRY_RUN` and `FRONT_DRY_RUN` are 0, and `V3_SELL_CHECK` is 0.
- The buy is `RELAY_V3.buy(token, 100, stake, minOut, deadline)`:
  - stake: the smaller of the family's 0.0058 ETH and the 0.004 ETH cap;
  - minOut: the launch-price quote × 0.97;
  - deadline: the launch block's time + 3 s.
- The sell is signed at the same time, at the next nonce: minOut 0, deadline + 2 h, 500k gas each.

**Landing:**
- Our buy can never share the launch's block: the feed only shows a block after it is sealed.
- Our recent v4 buys landed at +2 (124 of 131, and 56 of 58), occasionally +1 or +3 (REPORT_X).
- Ahead of a +2 buy there is only the +1 dust bot (0x776e5a2a), in 139 of 279 pools, at most 0.00223 ETH. That makes our fill at worst 0.9988 of the quote, far above the 0.97 minimum.
- The crowd's first real buy never came at +2 or earlier (0 of 279); 16 came at +3 to +5, and the median is +92. The buy lands in time.

**Failure costs** (ETH at $2,523.53):

| Case | Gas | Cost | Halt |
|---|---|---|---|
| Launch reverted: buy hits NoPool | about 31k | $0.0016 | none |
| …then the presigned sell finds nothing to sell | about 31k | $0.0016 | none |
| Buy past its 3 s deadline (slow sequencer) | about 26k | $0.0013 | none |
| Too much bought ahead of us (minOut fails) | about 235k | $0.012 | none |
| Pool pulled before our sell | sell runs out at the 500k limit | about $0.026, plus the whole stake (tokens worthless) | `HALTED.front.v3crowd` |

- No launch among the 349 reverted.
- Pull history: since Oct 10, 0 of 279 pools were pulled by +85 (the earliest was +86). Since Oct 3, 1 of 1,389 was pulled before an +80 sell (+79).

**A finding in the engine:** the live cap counts from our buy's actual block, not from the launch. The sell goes at our buy + 76, which is launch + 78 only when the buy lands at +2. A buy at +k sells at launch + 76 + k, up to about +110 within the 3 s deadline. 7 of 279 pools were pulled by +110. This only matters on a slow sequencer.

### 3. Side effects of going live

- **`V3_SELL_CHECK=0`** affects only crowd families (v3crowd is the only one). p356 is still checked before every buy, and it arms nothing anyway. The remaining risk is a new token template; a code-hash allowlist at arming would cover it. That is not built: the token is deployed 12 to 99 s before the launch, so the engine has time to read its code.
- **One slot, one nonce stream.** A live v3crowd trade holds the slot about 9 s (the sell lands around +80, then the receipts). At about 135 launches a day that is 1.4% of the day.
  - v2.433, paused by its operator since 02:07, would lose about 1.4% of its launches once it resumes.
  - v3crowd would lose about 2 to 3% of its launches while v2.433 trades, because it also waits for v2.433's pull check.
  - Dry fires (v3.0, p356) during a live V3 hold are skipped, so their counts read slightly low.
- **The streak halt.** `FRONT_NONBOT_HALT` (8) applies, because the v3crowd object has no `nonbot_halt`.
  - Only 32% of replayed trades net +2% or more.
  - 8 in a row under +2% happened 9 times in 279 launches. From a random start the halt comes after a median of 26 trades.
  - The longest natural run was 23. Set `"nonbot_halt":0` (rely on the pull halt) or 30.
- **`V3_DAILY_STOP_USD` (10).** The replay's running V3 day never dropped below −$0.01. Only a pull can reach the stop: one at 0.004 ETH costs $10.09. Front's own daily stop and daily count also stop v3crowd. A filled buy whose sell has no receipt halts all of front (`HALTED.front`), v2.433 included.
- **`V3_STAKE_CAP_ETH` (0.004).** For $5 set the family's `stake_eth` to 0.002. For $15, raise the cap to 0.006 and set `stake_eth` 0.006.

### 4. Owner steps, ETH and what to watch

**Before:** the gate decision. REPORT_W's gate is met on the replay:
- 279 launches at a +7.6% mean at $5;
- no pull before +85;
- 133 launches a day.

But:
- the median trade is −0.3% and the top 10% of trades bring about 80% of the profit;
- the line has paused today;
- a dry run cannot show how the operator reacts to us holding.

**Steps:**
1. On the box:
   ```
   cd ~/v2pons && git pull
   /opt/flip-venv/bin/python3 deploy/relay_v3_sim.py
   ```
   It must end "all as expected" (exit 2 means no live pool was found: rerun with `--hours 48`).
2. Check `results.py` shows no open trade, then `sudo systemctl stop flip-engine`.
3. Deploy the relay; it asks for a typed `yes`, then writes `RELAY_V3` and `RELAY_V3_CODEHASH` itself:
   ```
   sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_v3_deploy.py --write-env
   ```
4. Fund it and check it:
   ```
   sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py deposit_v3 0.005
   sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py status
   ```
5. Recommended, not in the docs: set `"stake_eth":0.002` and `"nonbot_halt":0` (or 30) on the v3crowd object, using the pattern of RUNBOOK 4j's step-2 snippet.
6. `set_kv V3_SELL_CHECK 0` (the helper from RUNBOOK 4j step 1).
7. `sudo systemctl start flip-engine`, then RUNBOOK 4j's step-3 check. It must show the relay verified, the code hash checked, the owner equal to the wallet, the cap and the relay's ETH.
8. RUNBOOK 4j step 2 (`sudo python3 - v3crowd live <<'PY' ... PY`), which restarts the engine. Check again: v3crowd `dry_run False live True` with its stake, and no `V3_SELL_CHECK` alarm.

To turn it off: the same snippet with `dry`, and remove `RELAY_V3` only after that.

**ETH:**
- The wallet holds 0.0136 ETH; the v4 relay holds 0.102 ETH.
- Deploy: about 1.07M gas, about 0.00002 ETH ($0.06).
- Deposit: 0.005 ETH.
- Gas: about $0.02 a trade from the wallet, about 0.0011 ETH ($2.70) a day at 135 trades. After the deposit the wallet keeps about 0.0086 ETH.

**What to watch:**
- `results.py`: the v3crowd LIVE row and the V3 relay's balance.
- `trade_done` lines with `"dex":"v3"`:
  - `buy_offset` should be 1 to 3; more means a slow sequencer and a stretched cap;
  - `sell_why` (the crowd's buy behind ours, or `deadline: launch + 78`);
  - `pull_after_buy_blocks`, `pulled_before_sell`, `ret`, `nonbot_streak`.
- The halt files `HALTED.front.v3crowd` and `HALTED.front`.
- Skips: "the relay holds less than the stake".
- Above all, the operator's reaction:
  - pulls in our pools against the baseline (earliest +86, median about 680);
  - whether the crowd's first buy still comes (about 37% by +78).

**Forward watch (15:27 to 16:00):** it saw only five pools of other shapes: four 13ead562 self-buyer pools with 8.7 to 11 KB tokens, and one launch that sent ETH. There was no new v3crowd launch, so the live sell-at-+80 simulation did not run.

No report .md was written, because the harness forbids report files; this answer is the report.

### Numbers

Launches Oct 10 00:00-Oct 12 13:44 UTC: 349 (Oct 10 132, Oct 11 147, Oct 12 70). WETH token0: 338, all eligible. WETH token1: 11, skipped.

Launch wallets:
- 349 distinct.
- 346 launch at the token's deploy nonce + 2; 3 sent a plain ETH transfer in between.
- 0 reverted launches. 0 pools created before the launch.
- Deploy to launch: 114 to 963 blocks (11.8 to 99 s).

Templates (all plain ERC20):
- 1,764 bytes, hash 0x19e3e2a6...00dc: 340 tokens.
- 5,048 bytes: 6 tokens, 6 hashes (only the metadata differs).
- 3,854 bytes, NEW (ERC20Burnable), hash 0x5fcfacb9...505b: 3 tokens.
- All: supply 1e27, 18 decimals, no owner, no external calls.

Tests on the latest state:
- Outsider transfer to the pool, transferFrom through SwapRouter02, transfer to a wallet: 349 of 349 succeed.
- Exact amounts arrive: 698 of 698.
- Relay round trip at 0.002 and 0.004 ETH on the 2 live pools: −0.0200% (two fees). Buy about 213k EVM gas (about 235k as a transaction); sell about 130k (about 152k).

Outsider sells:
- 1,317 sells in 298 of 349 pools: template A 1,256 (104 sellers), template C 56 (42 sellers), template B 5.
- Sell offset after the launch: 10th percentile +121, median +350, 90th percentile +1,964. 1,293 came at +78 or later, before the pull.
- 350 positions closed, realized median +17.7% (only those who sold).
- 1,207 positions held into the pull.
- Block scan (10 pools, +0 to +100): 40 transactions, 0 reverted.

Execution:
- Fill ahead of a +2 buy: worst 0.9988 of the launch quote (the +1 dust bot, at most 0.00223 ETH, in 139 of 279 pools).
- Crowd's first real buy at +2 or earlier: 0 of 279; +3 to +5: 16; median +92.

Failure costs at a base fee of 0.0205 gwei and ETH $2,523.53:
- NoPool buy: about 31k gas, $0.0016. The presigned sell then finds nothing to sell: about 31k gas, $0.0016.
- Past the deadline: $0.0013. minOut not met: $0.012. Sell on a pulled pool: out of gas at the 500k limit, about $0.026.

Pulls since Oct 10 12:00 (279 pools): by +85 none; by +90 1; by +100 4; by +110 7; the earliest at +86.

Streak halt (8 in a row under +2%):
- 32% of trades net +2% or more.
- 9 halts in 279 launches; the halt comes after a median of 26 trades (about 6.4 h); the longest natural run was 23.
- With a threshold of 25 or more: 0 halts.

Slot: about 9 s per trade, about 135 launches a day, so 1.4% of the day.

Stake: $5 = 0.00198 ETH, $15 = 0.00594 ETH; the cap of 0.004 ETH = $10.09.

Wallet 0.013599 ETH; v4 relay 0.102325 ETH. Relay deploy about 0.000022 ETH. Gas about 0.0000079 ETH a trade, about 0.00107 ETH a day.

RPC used: about 1,724 requests (10,000 items).

### Caveats

- **Read-only.** Public RPC only, one request at a time at least 0.6 s apart. No key used, nothing sent, nothing committed, no edits to src, deploy, tests or docs.
- **Latest state only.** The node keeps only about 1,000 blocks of state (older calls return "historical state not available"). All dynamic tests ran on the latest state. That is still conclusive for these templates: they have no owner, setter, time or caller checks that could switch a lock on later.
- **Borrowed data, read only.**
  - Outsider sells and positions come from the reaction agent's per-pool records, which it was rebuilding during my run. The +17.7% closed-position median counts only those who sold.
  - Replay returns, streaks and pull offsets come from the replay agent's per-launch rows (279 WETH-token0 launches, Oct 10 12:00 to Oct 12 13:44), not my own replay.
- **Reverted sells leave no logs.** The block scan covers only 10 pools from launch to +100 blocks. The nonce check is inconclusive, because the wallets do other things.
- **Gas figures** are EVM gas from eth_call plus 21,000 plus calldata. On our own receipts the L1 component was 70 to 1,300 gas.
- **The reaction is not measured here.** No dry run or replay can show the operator's reaction to our position; that is the sibling reaction study.
- **The forward watch saw no v3crowd launch** (15:27 to 16:00 UTC) and is stopped when this answer is returned. The line had not launched since 13:44.
- **Code changes suggested, not built:** a token code-hash allowlist at arming, and anchoring the cap at the launch rather than at our buy's block.
- **Disk full.** The disk filled up (ENOSPC) around 15:25 UTC; the session scratchpad holds 24 GB. I deleted only my own re-creatable `s02_code_cache.jsonl`; `s02_codes.py` refetches it.
- **No report file.** No .md was written, as the harness instructs; the report text is in the summary.

### Files

All in /home/user/v2pons/research/session_oct12/crowd/safety/:

Shared code:
- common.py, rpc.py (a copy of the reaction agent's paced client with eth_getStorageAt added), v3dec.py (a copy of the replay agent's decoder)

Research-only Solidity, never deployed, used through eth_call overrides:
- GasProbe.sol, TaxProbe.sol

Scripts and outputs:
- s00_probe.py/.out/.json: chain head, ETH price, archive depth
- s01_launches.py/.out/.json: the 349 launches
- s02_codes.py/.out/.json: token codes and templates
- s03_transfer_test.py/.out, s03_tokens.json: outsider transfer tests
- s04_outsider_sells.py/.out: outsiders' real sells
- s05_relay_sim.py/.out, s05a_receipts.py/.out: relay round trip, failure paths and gas
- s06_watch.py/.out/.jsonl: forward watch
- s07_nonce_check.py/.out: failed-sell nonce check
- s08_execution.py/.out, s08b_streaks.py/.out: execution timing and streak halt
- s09_block_scan.py/.out/.jsonl: reverted transactions after recent launches
- s10_launch_gaps.py/.out: launch wallets
- s11_balances.py/.out: wallet and relay balances
- s12_tax_probe.py/.out: exact-amount transfer test
- s13_value_launches.py/.out: 836-byte launches that sent ETH
- s14_cap_stretch.py/.out: pulls a late buy could reach
- s15_eligible.py/.out: launches the engine would arm
- s16_new_shapes.py/.out: the non-v3crowd pools seen during the watch

Ignored cache: s03_call_cache.jsonl

Inputs read (not modified):
- /home/user/v2pons/src/flip_engine.py
- /home/user/v2pons/contracts/FlipRelayV3.sol and FlipRelayV3.json
- /home/user/v2pons/docs/RELAY_V3.md, RUNBOOK.md (sections 4g, 4j), HANDOFF.md (16.16, 16.22)
- /home/user/v2pons/research/session_oct11/lines/REPORT_W.md, REPORT_X.md and analysis/W/
- /home/user/v2pons/research/session_oct12/crowd/replay/r06_rows.json
- /home/user/v2pons/research/session_oct12/crowd/reaction/r04_pools_cache.jsonl, r02_events_cache.jsonl, r03_txs_cache.jsonl, r16_early_pulls.out, r08_fronters.out

## Skeptic 1 (refuted: False)

### Measured

I wrote my own V3 pool model and replay. They live in /home/user/v2pons/research/session_oct12/crowd/skeptic1/, files k01 to k09 (.py and .out). I did not use the analyst's v3exact.py. All data came from the public RPC: about 350 POSTs, paced at 0.5 s or more. Nothing was edited or committed.

My model reproduces all 2,855 on-chain swaps in the launch windows exactly: amounts, sqrtP, L and tick.

I froze the head at block 86,801,281 (Oct 12 16:05 UTC). I found 289 launches of the line's shape from Oct 10 12:00, the same 289 the analyst found. 279 have WETH as token0; 10 have it as token1 and the engine skips them.

The line has not launched since 13:44:12 UTC. At 16:13 that was 2.49 h of silence.

Rule: our buy at the head of launch+2. The clock starts at the first buy the engine counts: a crowd call shape with an amount word between 0.005 and 10 ETH, or an ETH-value call carrying the token. The sell is sent at that buy +18 or at the +78 cap, and lands +2 (head of the block). Gas is 435k at each launch block's base fee (median 0.0200 gwei).

**Most recent 24 h (Oct 11 16:05 to Oct 12 16:05): 115 launches traded (118 in all)**
- 0.0012 ETH: mean +11.26%, median -0.64%, win 40/115, top 10% bring 92%.
  - Without the top 10%: +1.04%.
  - Without the best 5 trades: +3.58%.
  - Without the 8 launches of Oct 12 03:00-03:30: +3.93%.
  - Bootstrap 90% range of the mean: [+5.7, +17.6].
- 0.0058 ETH: mean +11.81%, median -0.06%, top 10% bring 88%.
  - Without the top 10%: +1.62%.
  - Without the best 5: +4.15%.
  - Without 03:00-03:30: +4.50%.
  - With the sell landing +1: +9.87%.
- Pulls: 112 of 115 pulled by the head. None at or before +80, none by +100, 7 by +150. Earliest +119, median +656. Every pull was by the launch wallet, through the NPM, removing 100% of the liquidity.

**The 24 h before (Oct 10 16:05 to Oct 11 16:05): 122 launches**
- 0.0012 ETH: mean +5.82%, median +0.09%, top 10% bring 55%, without the best 5 +4.31%.
- 0.0058 ETH: mean +6.38%, median +0.67%, top 10% bring 51%, without the best 5 +4.88%.
- Pulls: none before +80, 4 by +100, 15 by +150. Earliest +86, 94, 95, 98. Median +589.

**Their own window (279 launches)**
- Mean +7.32% at 0.0012 and +7.87% at 0.0058; median -0.62% and -0.05%; pulled before our sell: 0.
- Pulls: 275 of 279; none before +80; 4 by +100; 25 by +150; median +682.
- Every number I checked matches theirs: day and 6-hour slices, without 03:00-03:30 (+4.30/+4.87), caps 60/70/76/88/98, and their box 24 h (121 launches, +11.67% landing +2, +9.82% landing +1).
- Launch by launch, my returns are within 0.1 point of theirs on 279 of 279 (largest gap 0.041 point, from per-block base fee). Trigger offsets match on 279 of 279 and first-pull offsets on 279 of 279.

**ETH price:** the USDG/WETH 0.01% pool (5,327 WETH) gives $2,528. So 0.0012 ETH is $3.03, 0.0058 ETH is $14.66, and $5 is 0.0020 ETH.

### Reasons

Their numbers hold. On the same launches my independent code gives the same mean, median and pull counts within 0.04 point. On the two separate 24 h windows, both means are above +4% and no pull came before +80. So refuted=false.

What the split shows that the 2.1-day total hides:

1. **The latest 24 h rests on a few trades.** The +11.3/+11.8% comes from 5 of 115 trades, from two clusters (Oct 12 03:00-03:30 and 08:18-08:46). Without the best 5 the mean is +3.6% at 0.0012 and +4.2% at 0.0058, at or under the gate's +4%. The 24 h before is broader: its median is positive (+0.09/+0.67%) and it stays above +4% without its best 5. So "the median trade loses" is true of their whole window but not of every day.

2. **The latest 24 h misses the gate's rate.** Only 115 tradeable launches (118 in all) against the gate's 120 a day. The line has also been silent since 13:44 UTC (2.5 h at 16:13). Earlier gaps reached 3.6 h and 4.4 h, so this may only be a pause, but Oct 12 is now running at about 101 launches a day.

3. **Exact-block timing matters.** Moving the cap's sell from the head of +80 to +79 costs 1.7 points in the latest 24 h. Moving it to +78 costs 2.0 points (5.5 to 6.4 points to +78 on the other windows).
   - Two top trades had the crowd's first buy at +78/+79: -0.1% if we sell one block earlier, +188% or +52% if not.
   - At 9.71 blocks a second, the whole hold lasts 8.2 s. The earliest pull (+86) came 0.62 s after our +80 sell.

4. **Nothing here puts a position on chain.** The question of whether the operator reacts to a holder (as C-1's did, pulling 36 blocks, about 3.7 s, after our buy) is still untested. A pull before +80 would make a held trade -100%.

5. **Minor points.**
   - Their "top 10%" share uses 28 trades and mine uses 27; this explains the +1.40 vs +1.46 gap without the top 10%.
   - Both replays put our sell at the head of its block and re-simulate the crowd's sells by their on-chain token amount. These assumptions are the same in both, so the agreement does not test them.

## Skeptic 2 (refuted: False)

### Measured

I rebuilt the data from a fresh fetch with my own code. Read-only, public RPC only: 1,043 paced POSTs, about 160 HTTP 429s, no key, no transaction, no edits outside research/session_oct12/crowd/skeptic2/, nothing committed by me. A separate process auto-committed some of my small work files as research WIP.

REPLICATION
- Launches: my own decoder of PoolCreated and the 836-byte multicall finds 1,389 launches, the same set as the analyst (1,389 of 1,389). 61 have WETH as token1 and the per-day counts match.
- The head was 86,802,877 at 16:08 UTC. The last launch was at 13:44:12, so the line had been quiet for 2 h 24 min.
- Pulls: from my own logs to launch+300, 533 pools were pulled. The pull offset matches the analyst in 533 of 533, and every pull came from the launch wallet.
- The crowd's first real buy matches in 1,389 of 1,389.
- The engine's trigger (which also counts the Universal Router's 484-byte call) equals the analyst's trigger in all 1,389 pools.
- Pulled at or before our sell: 1 (0x29df8fd3, +79, Oct 4), and 0 of 618 since Oct 8. Both match the analyst.
- Block rate: 9.76 blocks/s (local p10-p90 9.6-9.9). So +80 is about 8.2 s, and a 3-block margin is about 0.3 s.

EARLY OUTSIDERS AND CLASSIFICATION
- A non-bot buy of at least 0.0005 ETH at +1..+10 happens in 284 pools (analyst: 274).
- True analogs of our trade (one buy of at least 0.0015 ETH at +1..+5): only 4 pools. The analyst's 11 sums several buys, and 7 of those 11 have a first buy of 0.0008-0.001 ETH.
- The +1 bot buys at +1..+3 in 821 pools.
- None of the 738 outside senders is the launch wallet of any line pool.
- The +1 bot's 8 WETH senders that are not pools are not crowd wallets, crowd contracts or launch wallets.
- Native-ETH funding cannot be traced: the node answers "historical state not available".
- 0x65050a9b is a shared trading-bot router used across many lines, including another operator's decoys (per the v2433 wallet study). Buying through it says nothing about who a wallet is.

DOSE: the cap branch (1,186 pools still alive at +79 with no trigger by +60)

| Non-bot ETH held at +78 | n | Pulled by +90 | by +100 | by +150 |
|---|---|---|---|---|
| none | 318 | 0 | 2 | 12 |
| under 0.001 | 205 | 1 | 3 | 23 |
| 0.001-0.002 | 348 | 4 | 10 | 58 |
| 0.002-0.004 | 233 | 4 | 8 | 48 |
| 0.004 or more | 82 | 0 | 2 | 24 |

- Pulled by +80: 0 in every bin.
- Trend test (Cochran-Armitage): p 0.045 at +90, 0.01 at +100, 6e-6 at +120, 7e-14 at +150.
- More outside ETH also brings the no-crowd pull earlier. Spearman correlation of ETH held with the pull block: -0.27 (p 0.0009), or -0.35 counting the bot (p 1e-5).
- The p10 pull offset falls from +118 (no holder) to +95 and +92 for the larger bins. The minimum stays at +83 to +87.
- Pull hazard before the crowd, by age:
  - +3..+78: 1 pull in about 95,500 pool-blocks, at any amount held.
  - +79..+90: 9 pulls in about 10,500 pool-blocks, all in pools holding at least 0.001 ETH (1.3-2.1 per 1,000 blocks).

EXTRACTORS (46 wallets, each compared with itself before and after its first profitable sale into the wave, against matched holder pools)

| Outcome | Before | After |
|---|---|---|
| Pulled by +100 (observed/expected) | 1.09 | 1.08 |
| Pulled by +150 (observed/expected) | 1.15 | 1.02 |
| Crowd by +78 (observed/expected) | 1.00 | 0.95 |

There is no sign of targeting. The analyst's 1.44 for pulls by +150 is the general effect of holding, not learning.

DOES THE CROWD SKIP?
- Crowd's first real buy by +60 with no early holder: 11.1% without the bot, 12.6% with it.
- With an early holder under 0.001 ETH: 21%.
- With an early holder of 0.001-0.0015 ETH: 0 of 28. But 22 of those 28 are one wallet (0x3e0b2a2e) on Oct 5, a day with many no-crowd pulls, so this is confounded.
- With an early holder of 0.0015 ETH or more: 2 of 9.
- There is no robust skip.

NEW: PULLS SOON AFTER THE CROWD'S FIRST BUY

| Period | Pulled within 20 blocks of the trigger | within 30 |
|---|---|---|
| Oct 3-9 | 0 of 760 | 1 of 760 |
| Oct 10-12 | 3 of 311 (1.0%, Wilson 0.3-2.8%, Fisher p 0.024) | 8 of 311 (Fisher p 0.0003) |

- Within 40 blocks, by day: Oct 10 11 of 119, Oct 11 5 of 127, Oct 12 0 of 65.
- All 8 Oct 10-12 cases had a non-bot outside holder at the trigger: 8 of 203 such pools, against 0 of 108 pools holding only the bot or no one.
- The lags were 11, 15, 16, 22, 25, 30, 30 and 30 blocks. All 8 were full burns by the launch wallet after crowd buys of 0.012-0.25 ETH, with no crowd sells before the pull.
- None of them was in a pool with a trigger by +60: 0 of 67 since Oct 10, and the smallest lag there is 39 blocks.
- The closest case: 0x7d719e14 on Oct 11 06:44, trigger +71, our cap sell landing at +80, pull at +86.

MARGINS
- The smallest gaps between our sell landing and the pull were 3 blocks (Oct 5), 5, and 6 (Oct 5 and Oct 11).
- The analyst's "since Oct 8, 0 of 298 pulled by +90" counts only pulls before the crowd. Counting pulls after it too, the cap branch with a holder since Oct 8 has 1 pull by +90 (the +86) and 7 by +100, out of 313 pools.

### Reasons

Not refuted. My own fetch and code reproduce the core conclusion exactly: the same 1,389 launches, the same pulls and first real buys, the same 1 pull at or before our sell (0 since Oct 8). The reaction is real and mostly slow. In pools where the crowd has not come, the pull starts at about +83 whatever the amount held. Before +79 there is almost nothing: 1 pull in about 95,500 pool-blocks. I found no targeting of repeat extractors once wallets are compared with themselves, no robust crowd skip, and no operator-owned "outsiders" among the checks I could run.

The conclusion holds today, but it is narrower than stated, in four ways:
1. The analyst missed a new pattern. On Oct 10-11, pools with a non-bot holder were pulled 11-30 blocks after the crowd's first real buy (8 of 311 since Oct 10 against 1 of 760 before, p 0.0003; 3 of them within 11-16 blocks). That is anchored on the crowd's buy, not on the launch, and it is faster than our exit of 18 blocks sent, about 20 landed. It has not yet hit a pool whose trigger came by +60, and Oct 12 shows none. At the Oct 10-12 rate it would cost about $0.014 a trade (upper about $0.04). But it is exactly the "reaction faster than our exit" that halted C-1. The analyst's risk list (the cap's 3-block margin and the C-1 precedent) leaves out this second path through the trigger exit.
2. Dose: more outside ETH makes the no-crowd pull both more likely and earlier. Our 0.002-0.006 ETH stake puts every pool we trade into the highest bins, where the pull comes at a p10 of +92 and a minimum of +83. The margin is 3-10 blocks, which is 0.3-1.0 s at 9.76 blocks/s.
3. The "0.3-0.5% at 95%" bound describes pools as they are without us. For a live wallet buying our size at +2, there are only 4 true analogs (11 by the analyst's looser count), so the bound is 24-53%. The C-1 precedent (historical strangers 0 of 3 pulled, live 4 of 5) still applies.
4. "Since Oct 8, 0 of 298 by +90" leaves out the post-crowd pull at +86 on Oct 11, which came 6 blocks after our cap sell would have landed.

If v3crowd goes live:
- Halt on any pull at or before the trigger+20 or before +90 in a pool where we hold.
- Watch the gap between the trigger and the pull every day.
- A shorter exit after the trigger in holder pools trades away edge, and that has not been tested.

Files are in /home/user/v2pons/research/session_oct12/crowd/skeptic2/, each script with a matching .out:
- rpc.py, common.py: the client and helpers
- s01_launches.py: own launch scan
- s02_logs.py: pool logs to +300
- s03_txs.py: transactions
- s04_build.py: per-pool records
- s05_dose.py: early outsiders, dose bins, hazard, crowd timing, bot, by day
- s06_extractors.py: within-wallet extractor test
- s07_quick_pulls.py: pulls soon after the trigger
- s08_timing_dose.py: pull timing against amount held
- s09_followers.py: follower bots and the regime change
- s10_crowd_skip.py: crowd skip by holder size
- s11_quick_holders.py: quick pulls by holder presence
- s12_quick_by_day.py: quick pulls by day

The caches are s02_logs_cache.jsonl, s03_txs_cache.jsonl and s04_pools_cache.jsonl, all git-ignored.
