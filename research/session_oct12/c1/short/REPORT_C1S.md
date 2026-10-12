# REPORT_C1S: can a short hold or a take-profit on C-1 sell before the operator reacts? (Oct 12, 2026)

The analyst: **NO EXIT BEATS THE REACTION**. Skeptic 1 (the reaction regime): refuted False. Skeptic 2 (execution): refuted True. The split is adjudicated separately (see REPORT_C1S_JUDGE.md when present).

## Analyst: best exit

No hold_blocks or take_profit setting earns enough before the reaction to be worth a test. Keep the halt.

- **The only exit never pulled is hold_blocks 10** (take_profit 9). It sells at buy+10 and lands at buy+12. Gross return:
  - +0.65% in the 31 holder-regime pools, 0 pulled.
  - +0.34% in the 10 pools held from T+2, which is the exact regime.
  - That is about the $0.02 gas: expected value is +$0.013 at $5 and -$0.003 in the exact regime.
- **The best mean is take_profit 0.06-0.08 with hold_blocks 45-50**: +1.6% to +2.0% over the 31 pools, but 1 pulled. In the exact regime it is -7.5% to -8.2%.
- **Every exit of 15 blocks or more is pulled at least once.**
  - 0xcf1d880b was pulled at T+19, 17 blocks after our entry. An outsider had held there since T-140.
  - 0xb47b706f was pulled at T+38.
  - 0x91620507 was pulled at T+63.
- **The current hold 60 is the worst setting where a holder is present**: -3.1% in the 31 pools, -27.7% in the exact regime.
- **Why no exit works.** The profit comes from the router's buys, and in our pools those land at buy+7 to +47. When a holder is present the router stops at buy+27 to +47, and the pull follows at buy+36 to +115. An exit long enough to collect the router's buying is also long enough to be pulled.
- **A dry test cannot settle this.** A dry position is not in the pool, so the operator never reacts to it, and a dry run only measures the no-holder path, which this study already measured.
- **Short holds would also trip the engine's own non-bot halt.** That halt fires after 5 trades in a row under +2%, and 68-87% of short-hold trades pay under +2%.
- **Side observation, not a fix.** Every early pull came in a pool whose trigger was after launch+100 (T at 103, 155, 194).
  - With trigger max_blocks 100, no pool in the data was pulled before T+64.
  - In the exact regime the plain hold 60 then beats any short hold: +2.8%, against +1.5% at hold 40 and +0.8% at hold 30 (n=5).
  - This cut was chosen after looking at the data, the margins are thin, and the operator can pull earlier (pools with no trigger were pulled at launch+64 to +143). It does not change the verdict.

## Analyst: exits table

Gross returns at 0.002 ETH, T-aligned: our buy at the end of block T+2, sell lands 2 blocks after it is sent, -100% if pulled in or before the landing block. Hold returns at 0.0058 ETH differ by at most 0.07pp (only take-profit exits move, because the gas threshold is a smaller share of a larger stake). "Pulled" means pulled before the sell lands.

Holder regime = ours + outside holders + 0xbd9dc5f6's pools from 13:15 (n=31). Held from T+2 = ours + holders who bought at or before T+5 (n=10). No holder = n=154.

| Exit | Holder regime: n, mean, median, up, pulled | Held from T+2: mean, up, pulled | Holder-aligned: mean, pulled | No holder: mean, median, up, pulled |
|---|---|---|---|---|
| hold 5 | 31, +0.47%, -0.02%, 4, 0 | +0.02%, 2, 0 | +1.59%, 0 | +0.48%, -0.02%, 13, 0 |
| hold 10 | 31, +0.65%, -0.02%, 6, 0 | +0.34%, 3, 0 | +2.51%, 0 | +1.09%, -0.02%, 28, 0 |
| hold 15 | 31, -2.39%, -0.02%, 10, 1 | -9.66%, 3, 1 | -0.45%, 1 | +1.18%, -0.02%, 33, 0 |
| hold 20 | 31, -2.04%, -0.01%, 12, 1 | -8.97%, 3, 1 | +0.08%, 1 | +1.58%, -0.02%, 41, 0 |
| hold 25 | 31, -0.98%, +0.01%, 16, 1 | -8.96%, 3, 1 | +0.70%, 1 | +1.83%, -0.02%, 45, 0 |
| hold 30 | 31, +0.09%, +0.04%, 18, 1 | -7.53%, 4, 1 | +1.76%, 1 | +2.99%, -0.01%, 57, 0 |
| hold 40 | 31, -2.47%, +0.17%, 22, 2 | -19.23%, 4, 2 | -1.24%, 2 | +5.24%, +1.43%, 89, 0 |
| hold 60 (now) | 31, -3.08%, +4.02%, 26, 3 | -27.70%, 6, 3 | -9.26%, 5 | +9.23%, +5.53%, 118, 0 |
| tp 2% cap 30 | 31, -1.34%, +0.04%, 18, 1 | -9.26%, 4, 1 | +0.02%, 1 | +2.39%, -0.01%, 57, 0 |
| tp 3% cap 30 | 31, -1.02%, +0.04%, 18, 1 | -8.56%, 4, 1 | +0.25%, 1 | +2.47%, -0.01%, 57, 0 |
| tp 4% cap 30 | 31, -1.02%, +0.04%, 18, 1 | -8.56%, 4, 1 | +0.28%, 1 | +2.51%, -0.01%, 57, 0 |
| tp 6% cap 30 | 31, -0.53%, +0.04%, 18, 1 | -8.56%, 4, 1 | +0.41%, 1 | +2.79%, -0.01%, 57, 0 |
| tp 8% cap 30 | 31, -0.53%, +0.04%, 18, 1 | -8.56%, 4, 1 | +0.41%, 1 | +2.91%, -0.01%, 57, 0 |
| tp 2% cap 60 | 31, -1.63%, +3.45%, 27, 2 | -17.39%, 7, 2 | -5.72%, 3 | +5.19%, +3.84%, 118, 0 |
| tp 3% cap 60 | 31, -1.17%, +4.00%, 27, 2 | -16.69%, 7, 2 | -8.82%, 4 | +5.35%, +4.12%, 118, 0 |
| tp 4% cap 60 | 31, -1.14%, +4.66%, 27, 2 | -16.69%, 7, 2 | -8.40%, 4 | +5.53%, +4.77%, 118, 0 |
| tp 6% cap 60 | 31, -0.65%, +4.66%, 27, 2 | -16.69%, 7, 2 | -8.20%, 4 | +6.16%, +5.53%, 118, 0 |
| tp 8% cap 60 | 31, -0.32%, +4.66%, 27, 2 | -16.69%, 7, 2 | -7.63%, 4 | +6.74%, +5.53%, 118, 0 |
| tp 6% cap 45 (extra) | 31, +1.64%, -, -, 1 | -8.21%, -, 1 | -2.12%, 2 | +5.13%, -, -, 0 |
| tp 6% cap 50 (extra) | 31, +1.95%, -, -, 1 | -7.55%, -, 1 | -1.88%, 2 | +5.37%, -, -, 0 |

Sub-groups of the holder regime (T-aligned):

| Sub-group | hold 10 | hold 20 | hold 30 | hold 60 |
|---|---|---|---|---|
| Ours (n=5) | +0.62%, 0 pulled | +2.01%, 0 pulled | +4.88%, 0 pulled | -17.17%, 1 pulled |
| Holder bought later than T+5 (n=16) | +1.06% | +1.66% | +4.67% | +10.29%, 0 pulled |
| 0xbd9dc5f6 from 13:15 (n=7) | -0.02% | +0.49% | +1.93% | +4.74%, 0 pulled |

Per 6-h slice (T-aligned, mean gross at hold 10 / 20 / 30 / 60, pulled in brackets):

| Slice (UTC) | Holder regime | No holder |
|---|---|---|
| Oct 11 01-07 | n=2: +0.2 / +0.2 / +0.2 / +4.4 | n=17: +2.7 / +4.0 / +5.5 / +16.4 |
| Oct 11 07-13 | none | n=15: +0.5 / +0.8 / +1.8 / +11.2 |
| Oct 11 13-19 | n=3: 0.0 / 0.0 / 0.0 / -32.3 (1) | n=31: +0.5 / +0.8 / +1.7 / +6.9 |
| Oct 11 19 to Oct 12 01 | n=7: 0.0 / -14.3 (1) / -13.7 (1) / -12.7 (1) | n=7: +0.1 / +0.1 / +1.5 / +6.4 |
| Oct 12 01-07 | n=2: +1.6 / +5.0 / +10.2 / -48.3 (1) | n=9: 0.0 / 0.0 / +2.5 / +11.1 |
| Oct 12 07-13 | n=6: +0.4 / +1.4 / +5.0 / +14.5 | n=68: +1.4 / +2.0 / +3.2 / +8.4 |
| Oct 12 13:00-14:14 | n=11: +1.3 / +1.6 / +4.4 / +8.3 | n=7: +0.7 / +0.7 / +5.1 / +6.5 |

## Analyst: reaction speed

Yes, the operator could react faster. The pull is one PositionManager transaction from the launch wallet. Pools with no trigger were pulled as early as launch+64, 133, 139 and 143. The other operator, the volume bot, reacts in about 9 blocks.

What C-1 has done so far (s05_reaction.out, 106 positions of at least 0.001 ETH held into a pull that came within 600 blocks of the buy):

| Measure | Shortest seen | Detail |
|---|---|---|
| Holder's buy to the router's last buy | 22-27 blocks | 22: 0x89b1da45 in 0xe96cdeb2. 23: 0xbd9dc5f6 in 0xd6bd637c. 27: ours in 0xb47b706f. Median 94 over 101 positions. |
| Router's last buy to the pull | 0 blocks | Median 22; 9-68 in our pools. |
| Holder's buy to the pull, in a reaction pool | 36 blocks | Ours, 0xb47b706f. Next: 45 and 54 (0xbd9dc5f6; at 45 the router had already stopped before its buy), 65 (0x5b0320fb, pool with no trigger), then 72, 75, 86, 91. |
| Our entry (T+2) to the pull | 17 blocks | 0xcf1d880b, pulled at T+19. An outsider had held there since T-140. |

- The 3- and 23-block lags in the list are late buys (T+300 and T+3990) that landed on top of a pull already under way. They are not reactions.
- In our 4 pulled pools the router bought at buy+30, +47, +37 and +7/+17/+27, then stopped. The pulls came at buy+97, +115, +84 and +36.
- **The timing looks tied to pool age, not to a fixed lag after the holder's buy.**
  - Pools that reacted were pulled at launch+147 to +213 (ours: 147-193).
  - No pool with a trigger, out of 189, was pulled before launch+147.
  - So a late trigger leaves a short hold no margin: in 0xcf1d880b the pull came 17 blocks after our would-be entry.

## Analyst: dollars

EV = stake × mean gross - $0.02 gas per trade (the engine's own round trip at 0.02 gwei is about $0.013). $5 uses the 0.002 ETH returns and $13 uses the 0.0058 ETH returns. CIs are 95% pool bootstraps (10,000 resamples). Break-even pull rate = (w - g) / (1 + w), where w is the survivors' mean and g = gas / stake.

**Holder regime, T-aligned (n=31):**

| Exit | Mean | Pulled (Wilson 95%) | Survivors' mean | Break-even pull rate $5 / $13 | EV at $5 [CI] | EV at $13 [CI] |
|---|---|---|---|---|---|---|
| hold 10 | +0.65% | 0/31 (0-11%) | +0.65% | 0.2% / 0.5% | +$0.013 [-0.016, +0.050] | +$0.065 [-0.009, +0.163] |
| hold 30 | +0.09% | 1/31 (1-16%) | +3.43% | 2.9% / 3.2% | -$0.015 [-0.405, +0.234] | -$0.008 [-1.02, +0.64] |
| tp 6% cap 45 | +1.64% | 1/31 | +5.03% | 4.4% / 4.6% | +$0.062 [-0.339, +0.349] | +$0.193 [-0.849, +0.939] |
| tp 6% cap 50 | +1.95% | 1/31 | +5.35% | 4.7% / 4.9% | +$0.078 [-0.326, +0.362] | +$0.233 [-0.815, +0.972] |
| hold 60 (now) | -3.08% | 3/31 (3-25%) | +7.30% | 6.4% / 6.7% | -$0.174 [-0.796, +0.340] | -$0.421 [-2.04, +0.92] |

- **Held from T+2 (n=10):**
  - hold 10: EV -$0.003 [-0.021, +0.029] at $5, +$0.024 [-0.022, +0.108] at $13.
  - Every longer exit: -$0.40 to -$1.41 at $5.
- **Holder-aligned (entry right after the holder's buy):**
  - hold 10: +2.51%, EV +$0.106 [+0.007, +0.256] at $5 and +$0.306 [+0.051, +0.697] at $13. One pool (0x5a9137ee, +39.5%) supplies about half of that mean, and the entry is at T+15..121, not our T+2.
  - hold 30: +$0.068 [-0.38, +0.44] at $5.
- **Our 5 fills:**
  - tp 6% cap 50: +4.85%, EV +$0.222 [+0.081, +0.382] at $5 and +$0.610 [+0.242, +1.024] at $13.
  - hold 30: +4.88%, EV +$0.224 [-0.021, +0.634] at $5.
  - But n=5, and 0xb47b706f alone (+10.1% to +20.5%) carries the mean. The median is about 0%.
- **No-holder pools, for contrast:** hold 60 +$0.44 [+0.35, +0.54] at $5 and +$1.18 at $13; hold 30 +$0.13; hold 10 +$0.03.

The best short exit is worth about $0.01-0.08 a trade at $5, with confidence intervals reaching -$0.33. That is not enough to test.

## Analyst: evidence

## Data
- **Range:** blocks 85,436,881 to 86,735,446 (Oct 11 01:00 to Oct 12 14:14 UTC). This is the C1R cache plus my extension to the head.
- **Extension (s01):** 20 new C-1 launches, 6,948 new events, 841 transactions.
  - 53 POSTs through the unchanged paced ../rpc.py (0.5 s apart, 11 HTTP 429s, backed off). Its log was redirected to short/.
  - Read methods only, public RPC only, no key, no transaction.
  - 0 relay swaps since the C1R cache.
- **Build (s02):** the c05 logic, plus each swap's exact wei amount and fee field and the launch sqrtP.
  - 208 pools, 189 with T, 205 pulled, all by the launch wallet.
  - 0 swaps unattributed in the windows measured.
- **Usable pools: 185.** Left out:
  - 19 with no trigger.
  - 2 launched at a different sqrtP; the engine would not arm them.
  - 2 where the outsider sold again by T+62.

## Pool math (src/v4math, validated in s03)
- While validating I found that the Swap log's fee field is 125 in 73 of the 208 pools once a 25-pip protocol fee switches on. This is rare inside T..T+70.
- With each swap's own fee, the integer replay reproduces all 91,429 recorded sqrtP values (0 above 1e-9 step by step; 3e-18 over the whole path T..T+200).
- Our 5 fills reproduce exactly: tokens to 4e-20, and gross +4.02 / +6.66 / -0.01 / +3.46% and -100%, matching the box log.

## Model (sim.py)
- **Entry:** our buy at the end of block T+2. In our own 5 pools, at its real place, with our real buy and sell taken out and re-simulated.
- **Our buy is inserted into the replay,** so it shifts every later price; this is not a linear approximation.
- **Hold N:** the sell is sent at buy+N, lands at +N+2, and is priced at the top of the landing block. A pull in or before the landing block counts as -100%.
- **Take-profit:** modelled on the engine's own price copy. That copy starts from the launch state, applies every buy and no sells, and uses fee 100.
  - It is checked on every buy behind ours: (sell_out_int - stake - 250,000 × 0.02 gwei) / stake ≥ tp.
  - The sell lands 2 blocks after the triggering buy, at the real pool price. The cap is hold_blocks.
- **Sensitivity (s07):** landing one block later, or at the end of the block, moves only hold 30 (+0.56pp) and hold 60 (-0.41pp).

## Regimes (groups.py)
- **Ours:** 5 pools.
- **Holders (c11 rule):** 21 pools. 5 early (bought at or before T+5); 16 later (T+15..56; mostly 0x5b0320fb and 0xbd9dc5f6).
- **0xbd9dc5f6 from 13:15:** 7 pools. Its buy came at T+18..121, after T+62 in 5 of them.
- **No holder:** 154 pools.
- **Holder-aligned version:** entry right after the holder's own buy, i.e. on the reaction's clock.

## Results
- **Where the profit comes from.** In no-holder pools the median pool sees no router buy before T+29. The gain arrives at T+30..60: hold 30 +3.0%, hold 60 +9.2%.
- **What happens with a holder.**
  - The router stops at buy+27..47 and the pull follows. Pulls before the hold ended came at T+19 (an outsider held since T-140), T+38 (ours), and T+63 (an outsider held since T-23).
  - All three were in pools whose trigger came after launch+100.
  - So no exit is both long enough to collect the router's buying and short enough to beat the pull: exits of 15-30 blocks are caught at T+19, and exits of 40-60 at T+38 and T+63.
- **Sub-groups:**
  - Late holders (T-aligned) were never pulled inside 60 (hold 60 +10.3%), because the reaction clock started after our entry.
  - 0xbd9dc5f6 from 13:15, holder-aligned: hold 10 +1.6%, hold 30 +3.0%, 0 pulled; hold 60 has 2 pulled.
  - In our own 5 fills, a short exit would have turned the -17% into +4.9%. That gain is one pool (0xb47b706f).
- **Trigger window (s07, s08).** With T ≤ 100 (family trigger max_blocks 100 instead of 400), no pool was pulled before T+64: 0 of 15 in the holder regime, 0 of 86 overall.
  - Held from T+2 with T ≤ 100 (n=5): hold 10 0.0%, hold 30 +0.8%, hold 40 +1.5%, hold 60 +2.8%.
  - So the trigger offset matters, not the hold; a short hold is no better than hold 60 there.
  - This is in-sample, and the margin is thin: hold 60 with T=100 lands at launch+164, against the earliest pull of a triggered pool at launch+147.
- **Operational notes.**
  - With a short hold, 68-87% of trades pay under +2%. FRONT_NONBOT_HALT=5 would halt the family unless its nonbot_halt is set to 0.
  - A dry run cannot observe the reaction, because the operator only reacts to a real position.

Nothing in src/, deploy/, tests/ or docs/ was edited, and I made no commit. Commits a6fc298 and e7630bc, which add earlier versions of short/ files, were made by someone else; s07-s09 are still untracked.

## Skeptic 1 (refuted: False)

### Measured

I wrote my own code and ran it offline on the cached raw logs: c02_events plus s01_events_new, the txs and the launches. I sent no RPC calls, edited nothing in src/deploy/tests/docs, and committed nothing. All files are in /home/user/v2pons/research/session_oct12/c1/short/skeptic1/ (k01-k09, .py and .out).

**Method**
- k01 rebuilds the 208 pools from the raw logs with my own buyer classes (k01_build.out).
- T is the engine's real trigger: the first router buy of at least min_eth 0.005 within max_blocks 400, from the c1 object in the RUNBOOK.
- The k02 replay is independent of sim.py. It carries every later swap over by its realised move (the change in Q96/sqrtP for a buy, in sqrtP for a sell) at 80-digit precision. Our own buy and sell use v4math.buy_out_int and sell_out_int.

**Validation (k03)**
- Our 4 real sells are reproduced to the wei: 2080326106421210, 2133169319847626, 1999790821960851 and 2069243258298840. Gross returns are +4.02%, +6.66%, -0.01% and +3.46%; 0xb47b706f was pulled at buy+36. These match the box log.
- Against the analyst's s04_exits.json (185 pools, every hold and take-profit exit), the largest difference is 0.

**Regime: ours plus an outsider holding at T+2..T+10, engine T, n=11 (k04)**
- My set differs from the analyst's 10. 0x8985e55f is out: the engine would never fire there, because its router buys were 0.00297, 0.004 and 0.00495 ETH, all under 0.005. 0xe12fa945 and 0x049464f8 are in.
- Results (k07):
  - hold 10: +0.83%, 0 pulled, EV +$0.021 at $5 [-0.018, +0.080].
  - Every exit of 15 blocks or more: 1 pulled (0xcf1d880b).
  - hold 30: -6.5%. tp 4% cap 40: -6.95%. hold 60: -25.5% (3 pulled).
- My code also gives the analyst's own 10-pool set exactly: hold 10 +0.34%, hold 30 -7.53%, hold 60 -27.70%.

**Our 5 real fills alone (k07)**

| Exit | Mean gross | Pulled | EV at $5 [95% CI] |
|---|---|---|---|
| hold 10 | +0.62% | 0/5 | |
| hold 30 | +4.88% | 0/5 | |
| tp 4% cap 30 | +2.81% | 0/5 | |
| tp 4% cap 40 | +3.51% | 0/5 | +$0.155 [+0.014, +0.323] |
| tp 4-8% cap 50 | +4.85% | 0/5 | |
| hold 60 (now) | -17.2% | 1/5 | |

- Wilson upper bound on the pull rate with 0/5: 43%.
- Leaving out 0xcf1d880b (n=10): tp 4% cap 40 gives +2.36%, 0 pulled, break-even pull rate 1.9%, Wilson upper 28%.

**0xcf1d880b is a different case**
- An outsider, 0x5373fb35, bought 0.00198 ETH at T-140.
- The router bought only at T (launch+194: 0.08 + 0.28 ETH) and never again. The pull came at T+19 (entry+17).
- 0x91620507 is the same pattern: holder at T-23, one router buy at T, pull at entry+61.
- Holders already in place at T are 3 of 182 triggered pools (1.6%), but they are 10-27% of the regime sets.

**Router timing after our entry E (k05)**
- Pools with a router buy within E+10 / E+20 / E+30:
  - No-holder pools (n=155): 16% / 26% / 36%.
  - Regime pools: 18% / 18% / 27%.
  - Our 3 reverted-buy pools (the engine fired, no position): 0/3 within E+30.
- First router buy after E: median E+37 in no-holder pools and in ours (ours: 30, 47, 76, 37, 7). The reverted-buy pools: 34, 37, 53.
- In ours the router ran one more buy, its last, at E+7..47, and the pull came 9-68 blocks later. A take-profit triggered by that buy lands 2 blocks after it.
- In the outsider-held regime pools the router came back within E+45 in only 1 of 6 (at E+1).

**Holder-aligned (k08): our buy right behind each outsider buy of at least 0.001 ETH, made at T+1..T+130 and held, n=39 including ours**

| Exit | Mean | Pulled |
|---|---|---|
| hold 10 | +2.40% | 0 |
| hold 30 | +6.34% | 0 |
| tp 4% cap 40 | +4.66% | 0 |
| tp 6% cap 50 | +2.78% | 1 (0xb63adb7e, pulled at h+45 with no router buy) |
| hold 60 | +0.50% | 3 |

**Shortest reaction lags (k06)**
- Holder's buy to pull: 36 (ours, 0xb47b706f), 45 and 54 (0xbd9dc5f6), then 58-75.
- The 3- and 23-block lags are late buys landing on top of a pull already under way.
- Triggered pools were never pulled before launch+147; pools with no trigger were pulled from launch+64.

**What a dry run would show (k09)**
- The no-holder path for tp 4% cap 40: +3.75%, 0 pulled, but 88 of 155 trades under +2%.

**Trigger window max_blocks 100 (k09)**
- Regime, n=5: hold 60 +3.58% is better than tp 4% cap 40 at +2.59%. Both 0 pulled.
- Every pull at an exit of 30 or more falls in pools with T above 100.

### Reasons

I could not refute the decision: keep the halt and run no short-hold dry test. The analyst's numbers are exact (my independent replay matches to the wei and gives a difference of 0 on every exit), and on my lens's three questions the evidence does not support acting on any hold_blocks/take_profit setting.

**1. Is the router's buying early after a holder appears enough to pay?**
- For 25 blocks or less: no. Router buys in the first 10-20 blocks after entry are as rare with no holder (16-26% of pools) as in the regime (18%).
- So hold 10 earns about the gas: +0.62% on ours, +0.83% in my regime of 11, EV about +$0.01-0.02 at $5.
- The profit sits in the router's next buy, which comes at about E+30..47 (median E+37 everywhere). That is the same window in which the reaction starts.

**2. Does the router stop faster than the exit?**
- Not in our 5. The router made one more buy and the pull came 9-68 blocks after it.
- A take-profit with a cap of 30-40 caught that buy, or exited flat, before the pull in 5 of 5 (+2.8% to +3.5%). The current hold 60 gave -17.2% on the same trades.
- In outsider-held pools, though, the router usually never came back (4 of 6), so the same exit earns about 0.

**3. Is the sample big enough to act on?**
- No. The candidate exit rests on 0/5 (our fills) and 0/10 to 0/39 (other holder pools) pulls. That bounds the pull rate below 28-43% (9% for the 39 holder-aligned events), while break-even is about 2-4%.
- The fastest reactions to a holder who bought after T leave the candidate exits only 3-4 blocks of margin: cap 40 lands at 42 against a pull at 45, cap 30 at 32 against 36. A sell stall like the 11.5 s on Oct 12 00:00 (over 100 blocks) would turn that into -100%.
- Pulls 17-19 blocks after the trigger exist (0xcf1d880b).
- A dry test cannot measure any of this. The engine's dry position is not in the pool (take_profit puts the dry buy only into its own price copy), so it would show the no-holder +3.75% and trip the non-bot halt (88 of 155 trades under +2%).

**Where the write-up overstates its case (does not change the verdict)**
- **"Every exit of 15 or more is pulled" and the -7.5% to -9.7% exact-regime means** rest on one pool, 0xcf1d880b. There the reaction clock was started by a holder 140 blocks before T. Such pools are 1.6% of triggers but 10% of the analyst's exact set.
- **Where some exit did beat the reaction:** after reactions to a holder who bought after T, tp 4% with hold_blocks 30-40 was never pulled (ours 5/5; 34 outsider events). So "no exit beats the reaction" is literally false for the reaction to our own position. What nothing beats is the fast pull in pools that already had a holder before T.
- **"An exit long enough to collect the router's buying is also long enough to be pulled"** is not borne out. Take-profit exits collected the router's buys in 3 of our 5 pools and were never pulled. The one pulled pool had no router buy after entry at all.
- **Pool selection is slightly off.** 0x8985e55f is not an engine trade (its router buys were under min_eth 0.005). 0xe12fa945 and 0x049464f8 were wrongly dropped. Net effect is small.
- **The best case and its cost.** Reweighting 0xcf1d880b to its real frequency, the best candidate (hold_blocks 40, take_profit 0.04) is worth only about +$0.07 per trade at $5 at the point estimate, with a break-even of about 2%. Settling that would need a live test, not a dry one.

## Skeptic 2 (refuted: True)

### Measured

Skeptic 2, execution lens. I rebuilt the measurement with my own replay and modelled how the engine actually executes. The analyst's s02_pools.json, plus the router calldata in c03_txs and s01_txs, was used as data only. RPC use: 2 batched POSTs (16 receipts of our own transactions). No key, no transaction, and nothing outside research/session_oct12/c1/short/skeptic2/ was touched. I wrote no .md report; this answer is the report.

CHECKS
- My integer replay reproduces all 91,429 recorded sqrtP values exactly.
- The router's calldata word 2 equals the Swap log's ETH, with flag 0, in 9,415 of 9,415 router buys.

EXECUTION MODEL (taken from flip_engine.py)
- minOut: the engine fires on the first router buy of at least 0.005 ETH. minOut = buy_out_int at the engine's price copy (launch state plus every buy the feed shows, sells never), times 0.97 (BUY_SLIP 0.03).
- Our buy lands at the top of T+2 (75%) or T+3 (25%). It reverts below minOut.
- Take-profit is checked on the engine's own price copy (which ignores sells), using feed_tokens and the 250k-gas allowance.
- The sell is sent at buy+N, or at the take-profit block, and lands 1, 2 or 3 blocks later (25/50/25%) at the real pool price.
- The swap fee (100 pips, 125 where the 25-pip protocol fee applies) is charged on both the buy and the sell. Our own stake is replayed inside the pool, so its price impact counts.
- A pull in or before the landing block counts as -100%.
- Gas, from our own receipts: $0.011 per filled round trip, $0.022 for a fill whose sell met the pull (335k gas), $0.0045 per reverted attempt. The analyst used $0.02.

VALIDATION: the model reproduces all 8 of our real attempts.
- 5 fills, at +4.02%, +6.66%, -0.01%, +3.46% and -100%.
- 3 reverts, which fell 6.59%, 3.84% and 6.45% short of minOut.

WHAT CHANGES
- In the 31-pool holder regime the engine fills 23, not the analyst's 30.
- Of the other 8, seven revert on minOut and 0x8985e55f never triggers. Its router buys are all under min_eth 0.005; the analyst's T is under 0.005 ETH in 10 pools.
- **0xcf1d880b reverts.** A second router buy of 0.28 ETH in block T, after the 0.08 trigger, leaves our buy 5.3% short.
- That pool's pull at T+19 is the only one that made every exit of 15-50 blocks "pulled at least once" in the analyst's tables.
- With the analyst's settings (end of T+2, no minOut check, lag 2) my code reproduces the analyst's numbers: hold 30 at +0.10% with 1 pulled.

HOLDER REGIME (31 attempts, 23 fills), EV in $ per attempt (reverts included), 95% pool bootstrap:

| Exit | Pulled | Mean gross of fills | EV at $5 [CI] | EV at $13 [CI] |
|---|---|---|---|---|
| hold 10 | 0 | +0.87% | +0.022 [-0.006, +0.060] | +0.074 |
| hold 20 | 0 | +1.34% | +0.040 [+0.002, +0.089] | +0.120 [+0.021, +0.247] |
| hold 25 | 0 | +1.85% | +0.071 [+0.004, +0.155] | +0.200 [+0.026, +0.418] |
| hold 30 | 0 | +3.30% | +0.114 [+0.030, +0.221] | +0.313 [+0.092, +0.590] |
| hold 35 | 1 | -1.24% | -0.054 | – |
| hold 60 (now) | 2 | -1.63% | -0.070 [-0.61, +0.34] | -0.167 |
| tp 4% cap 30 | 0 | +1.81% | +0.062 [+0.019, +0.113] | +0.176 |
| tp 6% cap 50 | 0 | +5.81% | +0.209 [+0.098, +0.361] | +0.559 |

- **Execution sensitivity:** buy at T+2 or T+3, sell lag 1-3, top or end of block. Hold 30 stays between +$0.107 and +$0.128.
- **Leave one pool out:** hold 30 stays between +$0.084 and +$0.119.
- **Per filled trade:** hold 30 earns +$0.156 at $5 and +$0.423 at $13.

HELD FROM T+2 (10 attempts; 6 fills: our 5 and 0x91620507)
- hold 20: +$0.042 [-0.010, +0.143]
- hold 30: +$0.114 [-0.009, +0.319] at $5; +$0.310 [-0.009, +0.842] at $13; leave one pool out +$0.014 to +$0.128.
- tp 6% cap 50: +$0.113 [+0.014, +0.224]
- hold 60: -$0.94
- Our own 5 fills: hold 30 gives +4.88% gross with 0 pulled. Hold 60 gives -17.2% with 1 pulled.

NO HOLDER (154 attempts, 111 fills)
- hold 30: +2.10%, +$0.067 [+0.039, +0.097]
- hold 60: +5.24%, against the analyst's +8.92%, because minOut drops the pools with the strongest early router buying.

PER 6-H SLICE, hold 30, holder regime (fills/attempts, mean gross of fills); 0 pulled in every slice

| Slice (UTC) | Fills | Mean gross |
|---|---|---|
| Oct 11 01-07 | 0/2 | – |
| Oct 11 07-13 | no regime pools | – |
| Oct 11 13-19 | 3/3 | 0.0% |
| Oct 11 19 to Oct 12 01 | 5/7 | +0.8% |
| Oct 12 01-07 | 2/2 | +10.2% |
| Oct 12 07-13 | 3/6 | +1.0% |
| Oct 12 13:00-14:14 | 10/11 | +4.8% |

Hold 60 was pulled once in Oct 11 13-19 and once in Oct 12 01-07.

REACTION MARGIN (k06)
- 18 positions were bought between the engine's trigger and T+150 and still held when their pool was pulled.
- Shortest buy-to-pull lags: 36 (ours, 0xb47b706f), then 45, 54, 72.
- None came within 33 blocks, so hold 30 (landing at buy+31 to +33) beats every one. Hold 35 is hit once.

A FASTER OPERATOR, applied to every fill in all 185 pools (EV at $5 / $13)
- Treated like its fastest-ever case, 0xb47b706f (router stops at buy+27, pull at buy+36):
  - hold 30: +$0.059 / +$0.168
  - hold 25: +$0.053 / +$0.153
  - tp 4% cap 30: +$0.042 / +$0.123
- Hold 30 stays positive until the pull comes at or before buy+33. From that point it loses about $3.6 per attempt at $5.
- Hold 25 survives a pull as early as buy+29, hold 20 one as early as buy+24.

TRIGGER WINDOW (max_blocks)
- 100: holder regime hold 30 +$0.134 [0.00, 0.31], n 14
- 150: +$0.101

BREAK-EVEN for hold 30
- The break-even pull rate is 3.0% at $5 and 3.15% at $13.
- 0 of 23 pulled gives only a 12.2% one-sided 95% upper bound, so the case rests on the 36-block minimum lag, not on the count.

NON-BOT HALT: hold 30 has 73% of its fills under +2%, so the default streak halt would trip 12 times over 134 fills. It is per-family config ("nonbot_halt": 0).

Files are in /home/user/v2pons/research/session_oct12/c1/short/skeptic2/: sk.py, k01_gas, k02_exec (the simulator), k03_tables, k04_stress, k05_detail and k06_lags (.py and .out), and rpc_log.jsonl.

### Reasons

I refute the verdict. "NO EXIT BEATS THE REACTION" rests on a fill model the engine does not follow. Under the engine's own execution, which I validated on all 8 of our real attempts, several short exits land before every reaction seen and pay at both $5 and $13.

1. **The analyst fills buys the engine would revert.**
   - minOut (3%) reverts 8 of the 31 holder-regime pools and 43 of the 154 no-holder pools.
   - Among them is 0xcf1d880b, the pool pulled at T+19 and the only early pull behind "every exit of 15 blocks or more is pulled at least once".
   - It is also behind the -7.5% to -9.7% the analyst reports for holds 15-30 in the held-from-T+2 group, and behind the one pull in tp 6% cap 45/50.
   - The engine would not have entered it: a second router buy of 0.28 ETH in the trigger block leaves our buy 5.3% short.
   - With that pool out, no exit landing at or before buy+35 is pulled: 0 of 23 regime fills, 0 of 134 fills in all.

2. **Short holds sell before the reaction.**
   - Hold 30 lands at buy+31 to +33. The fastest pull ever seen on a position bought from the trigger to T+150 is buy+36 (ours, 0xb47b706f), then 45 and 54 blocks.
   - In that pool, hold 30 collects the router's last buy at +27 and earns +20.5%.
   - On our own 5 fills, hold 30 earns +4.9% gross, 0 pulled.
   - So "an exit long enough to collect the router's buying is also long enough to be pulled" is not true at 20-30 blocks.

3. **The gains survive realistic execution.**
   - The mixture covers a buy at T+2 or T+3, a sell 1-3 blocks after it is sent, the fee both ways, our own impact, take-profit judged on the engine's copy, reverted buys costing gas, and the real gas of $0.011 rather than $0.02.
   - Holder regime, hold 30: +$0.114 per attempt at $5 [CI +0.030, +0.221] and +$0.313 at $13 [CI +0.092, +0.590]. Hold 20 and hold 25 also have CIs above zero.
   - Exact regime, hold 30: +$0.11 and +$0.31, with CI lower bounds of about -$0.01 (n=10).
   - Even if the operator gave every fill its fastest-ever treatment (stop at +27, pull at +36), hold 30 still earns +$0.06 at $5 and +$0.17 at $13 per attempt.

4. **Smaller errors in the analysis.**
   - In 10 pools the analyst's T is a router buy under the trigger's min_eth (0.005 ETH); 0x8985e55f never triggers at all.
   - Gas is overstated ($0.02 against $0.011 measured).
   - The non-bot halt objection is a per-family setting (nonbot_halt 0), and the RUNBOOK already describes using it for C-1-type lines.

5. **What still stands from the analyst.**
   - Hold 60 is bad in the regime: realistic -$0.07 per attempt at $5, and -$0.94 when held from T+2.
   - The operator could pull faster. Hold 30 has only 3-5 blocks of margin over the fastest reaction seen, and it loses about $3.6 per attempt at $5 once the pull comes at or before buy+33.
   - The samples are tiny. 0 of 23 pulled cannot statistically bound the pull rate under the 3% break-even (upper bound 12%), so the case rests on the 36-block minimum lag.
   - A dry position never provokes the reaction. Also, the engine's dry run does not apply minOut, so its fills must be post-processed from the logged min_out and feed tokens.

**Verdict: SHORT HOLD WORTH A DRY TEST.**
- **Settings:** c1 family hold_blocks 30, take_profit 9 (off). Take-profits with caps of 45 or more depend on the take-profit firing before reactions that come 36-54 blocks after the buy, and capped-30 take-profits earn less than plain hold 30. Set nonbot_halt 0 for c1.
- **More margin:** hold_blocks 25 gives up about 40% of the expected value (+$0.071 against +$0.114 at $5 in the regime) and stays safe while the operator pulls no earlier than buy+29.
- **Optional:** trigger max_blocks 100 keeps a sell landing at hold 30 before launch+147, the earliest pull of any triggered pool in the data.
- **Live trading stays halted.** The dry run can confirm fills and landing lags. Only a $5 live probe with the per-family pull halt armed can test the reaction itself.

## Files

All under /home/user/v2pons/research/session_oct12/c1/short/:

**Helpers**
- sc.py: imports ../common.py and the paced ../rpc.py, and redirects the RPC log here.
- sim.py: integer V4 replay, hold and take-profit exits, the engine's price copy.
- groups.py: pool regimes, usability rules, 6-h slices.

**Scripts and outputs**
- s01_extend.py, s01_extend.out: extension to the head. Caches: s01_meta.json, s01_launches_new.json, s01_events_new.jsonl, s01_relay_new.json, s01_txs_new.jsonl; RPC log in rpc_log.jsonl.
- s02_build.py, s02_build.out: merged per-pool build (cache s02_pools.json, 37 MB, git-ignored).
- s03_validate.py, s03_validate.out: replay and our-fill checks.
- s04_exits.py, s04_exits.out, s04_exits.json: every exit × regime × stake, slices, per-pool detail.
- s05_reaction.py, s05_reaction.out, s05_reaction.json: reaction lags.
- s06_summary.py, s06_summary.out: break-even, EV at $5 and $13 with CIs, trigger-offset split, router buys in our pools.
- s07_sensitivity.py, s07_sensitivity.out: max_blocks, landing, bd13, slices, early-pull list.
- s08_strict.py, s08_strict.out: the held-from-T+2 regime.
- s09_table.py, s09_table.out: compact exit table.

No .md report file was written; the full report is in this answer.
