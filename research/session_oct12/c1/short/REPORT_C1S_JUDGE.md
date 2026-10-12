# REPORT_C1S_JUDGE: two independent judges on the C-1 short-hold split (Oct 12, 2026)

## Judge 1: LIVE PROBE

### settings

These are the c1 settings for a $5 live probe, given as the box's FRONT_FAMILIES object. The engine needs no code change.

{"name":"c1","value_wei":0,"calldata_len":2276,"fee":100,"tick_spacing":1,"sqrt_p":"792280926924313289846529216293289","liq":"100000088127620690885293","bot_minout":1,"ahead_max_eth":0.5,"take_profit":9,"hold_blocks":30,"stake_eth":0.002,"dry_run":false,"pin":true,"nonbot_halt":0,"trigger":{"router":"0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6","selector":"e6cb474f","value_word":2,"token_word":8,"flag_word":7,"flag_value":0,"min_eth":0.005,"max_eth":10,"max_blocks":100}}

- **hold_blocks 30.**
- **take_profit 9 (off).**
  - At caps of 30, take-profit earns less than a plain hold 30.
  - At caps of 40, a trade where the take-profit never fires sells at the cap and lands at our buy + 42. That is past the fastest reaction seen (36).
- **Trigger max_blocks 100, not the box's 400.**
- **stake_eth 0.002 ($5).**
- **nonbot_halt 0, as on the box.** 77% of hold-30 fills pay under +2%, so the default streak halt would trip.
- **pin true: do not add the 14:00 launch shape.**
- **Steps:** remove HALTED.front.c1, then restart.
- **Stop rule.** The engine's own c1 halt fires on the first pull that lands before our sell. Stop by hand at 100 attempts: there is no per-family trade cap. At about 54 triggers a day, that is about 2 days.
- **More conservative alternative:** hold_blocks 25. It earns +$0.049 per attempt [+0.020, +0.084] with 9 blocks of margin, instead of 4.
- **Advisable:** set SELL_ALT_URL. It is not set on the box, and it cuts the tail risk of the sequencer stalling a sell (once, 11.5 s).

### fill model

How src/flip_engine.py (release 0.9) trades a trigger family:

**Arming (arm_front)**
- The launch is a 2,276-byte, value-0 PositionManager multicall: fee 100, ETH pair, no hook.
- With pin true, the launch sqrtP and the mint liquidity must equal the family's values exactly. Any other launch is logged as a new fingerprint and is not armed.

**The engine's price copy**
- It starts from the launch sqrtP (as a float) and the mint liquidity, and always uses fee 100.
- It applies every router call with flag word 7 = 0, using the amount in calldata word 2, up to max_eth 10.
- It also applies every transaction with ETH value that carries the token.
- It never applies a sell.

**Trigger (on_wave_call)**
- The first router buy of at least 0.005 ETH sets first_buy.
- It fires only if it lands within max_blocks of the launch and the feed is not stale. If that first buy is late, the pool never fires.
- A PositionManager call carrying the token before the trigger makes the pool late.

**Our buy (_fire)**
- The engine fires while processing the trigger transaction.
- min_out = int(buy_out_int(int(copy including the trigger), L, stake, 100) × 0.97).
- Later buys in block T are not in that copy.
- The buy lands at the top of T+2: 7 of our 8 attempts did; one sent late landed at T+7.
- It reverts when the pool gives fewer tokens than min_out. About 0.15 ETH of router buying between the trigger transaction and our buy is enough.
- The deadline is the block's timestamp + 3 s, which never binds here.

**After our buy lands (our_buy_landed)**
- feed_tokens = buy_out_int(copy at that point), then the copy adds our stake.

**When the sell goes**
- hold_blocks counts from the block in which our buy appears in the feed.
- The deadline sell is sent after processing the feed block buy + hold_blocks. For front families send_after equals hold_blocks, with no lead.
- It lands 1-2 blocks later. Our 8 c1 sells, all sent at buy+60, landed at buy+61 once and buy+62 seven times (including the 4 reverted ones).
- A wall-clock fallback sends the sell if the feed stalls: 0.5 + 0.11 × (hold − 2) s after the fire, which is 3.58 s for hold 30.

**Take-profit (take_profit)**
- On each router flag-0 buy or ETH-value buy behind ours, the engine computes, on the copy, (sell_out_int(copy, L, feed_tokens, 100) − stake − 250,000 × base fee) / stake.
- If that is at least tp, it sells at once. tp 9 means off.

**Pull check and halts (_settle)**
- It reads the ModifyLiquidity logs from our buy's block to the sell's block + 30.
- A pull that lands before our sell (by block and index) calls halt(scope front, fam c1) and writes HALTED.front.c1. Only c1 stops.
- A pull that lands after our sell halts nothing (the near-miss halt applies to follow only).
- A filled buy whose sell sold nothing halts all of front.
- With nonbot_halt 0, there is no streak halt.

**Check against our 8 real attempts**
My own replay (j02_sim) reproduces all 8:
- **5 fills:** +4.02%, +6.66%, −0.01%, +3.46%, and −100% (0xb47b706f, pulled at buy+36), at the real landing blocks.
- **3 reverts:** 0x35869115, 0xd4654e14 and 0x266d00f1 got 6.59%, 3.84% and 6.45% fewer tokens than the copy's quote; the limit is 3%.

Skeptic 2's model is right. 0xcf1d880b reverts by 5.33%, because the router bought 0.28 ETH in block T after its 0.08 ETH trigger. Without minOut, every exit of 15 blocks or more there would have been −100%.

One small correction: skeptic 2 assumed sell lags of 1/2/3 blocks at 25/50/25%. On chain it is +2 in 7 of 8 cases. This makes no material difference.

### cells

My replay (j03, j06, j08) uses the engine's fills, $5 = 0.002 ETH at $2,500, and gas from our own receipts. Rows are $ per attempt, with reverts counted. Brackets are 95% pool-bootstrap intervals (10,000 resamples). The data are the analyst's 208 pools plus the 10 C-1 launches since 14:14 that I fetched.

**max_blocks 400 (the box)**

(a) Holder regime: 30 attempts, 23 fills.

| Exit | $ per attempt [95% CI] | Pulled |
|---|---|---|
| hold 20 | +0.042 [+0.002, +0.093] | 0 |
| hold 25 | +0.062 [+0.004, +0.135] | 0 |
| hold 30 | +0.117 [+0.028, +0.228] | 0 |
| hold 35 | −0.057 [−0.443, +0.178] | 1 |
| tp 4% cap 30 | +0.060 [+0.016, +0.112] | 0 |
| tp 6% cap 30 | +0.085 [+0.022, +0.161] | 0 |
| tp 4% cap 40 | +0.104 [+0.052, +0.160] | 0 |
| tp 6% cap 40 | +0.129 [+0.060, +0.206] | 0 |
| hold 60 (for comparison) | −0.073 | 2 |

(b) All triggered pools: 185 attempts, 136 fills.

| Exit | $ per attempt [95% CI] | Pulled |
|---|---|---|
| hold 20 | +0.039 [+0.022, +0.058] | 0 |
| hold 25 | +0.050 [+0.030, +0.072] | 0 |
| hold 30 | +0.074 [+0.047, +0.105] | 0 |
| hold 35 | +0.057 [−0.015, +0.108] | 1 |
| tp 4% cap 30 | +0.055 [+0.035, +0.079] | 0 |
| tp 6% cap 30 | +0.066 [+0.042, +0.093] | 0 |
| tp 4% cap 40 | +0.085 [+0.061, +0.112] | 0 |
| tp 6% cap 40 | +0.099 [+0.070, +0.129] | 0 |

**max_blocks 100**

(a) Holder regime: 14 attempts, 14 fills, 0 pulled for every exit including hold 60.

| Exit | $ per attempt [95% CI] |
|---|---|
| hold 20 | +0.046 [−0.011, +0.120] |
| hold 25 | +0.086 [−0.011, +0.234] |
| hold 30 | +0.132 [−0.002, +0.310] |
| hold 35 | +0.165 [+0.027, +0.335] |
| tp 4% cap 30 | +0.060 [−0.002, +0.137] |
| tp 6% cap 30 | +0.100 [−0.002, +0.242] |
| tp 4% cap 40 | +0.130 [+0.053, +0.210] |
| tp 6% cap 40 | +0.170 [+0.059, +0.305] |

(b) All triggered pools: 84 attempts, 74 fills, 0 pulled.

| Exit | $ per attempt [95% CI] |
|---|---|
| hold 20 | +0.038 [+0.014, +0.067] |
| hold 25 | +0.049 [+0.020, +0.084] |
| hold 30 | +0.066 [+0.031, +0.108] |
| hold 35 | +0.075 [+0.038, +0.116] |
| tp 4% cap 30 | +0.046 [+0.022, +0.073] |
| tp 6% cap 30 | +0.061 [+0.029, +0.098] |
| tp 4% cap 40 | +0.076 [+0.047, +0.109] |
| tp 6% cap 40 | +0.093 [+0.057, +0.134] |

**Stress tests and other checks**
- Under a buy at T+3, or a sell lag of 1 or 3 blocks, hold 30 stays at +0.111 to +0.122 (holder regime, max_blocks 400) and +0.061 to +0.076 (all triggered pools).
- At $13 (0.0052 ETH), hold 30 earns:
  - max_blocks 400: +0.319 [+0.087, +0.608] in the holder regime and +0.208 in all triggered pools.
  - max_blocks 100: +0.361 [+0.013, +0.824] and +0.188.
- In our own 5 fills, hold 30 gives +4.88% gross with 0 pulled; hold 60 gives −17.2%.

**Margins** (lag 2: hold 20/25/30/35 land at our buy + 22/27/32/37; a cap-40 trade where the take-profit never fires lands at + 42)

Every known reaction, measured from the holder's buy:
- Positions bought from T to T+150 and held into the pull: 36 (ours, T 155), 45, 54, 72, 74, 75, 75, 80, 91, 116, 150, and later.
- Holders already in before T, measured from our would-be buy at T+2: 17 (0xcf1d880b, where the engine's buy reverts) and 61 (0x91620507).

Margin to the three fastest post-T reactions (36, 45, 54), and to the two pre-T ones:

| Exit | Lands at buy + | Margin to 36 / 45 / 54 | Margin to the pre-T pulls (17 / 61) |
|---|---|---|---|
| hold 20 | 22 | +14 / +23 / +32 | −5 / +39 |
| hold 25 | 27 | +9 / +18 / +27 | −10 / +34 |
| hold 30 | 32 | +4 / +13 / +22 | −15 / +29 |
| hold 35 | 37 | −1 / +8 / +17 | — |
| tp cap 30 | 32 at most | +4 at worst | — |
| tp cap 40 (no take-profit) | 42 | −6 | — |

**In the pools max_blocks 100 trades (T ≤ 100):**
- The reaction lags are 75, 80 and 91.
- The earliest pull after our would-be buy is buy+84.
- So hold 30 has a margin of +43 on the reaction lag and +52 on the earliest pull.
- On the pool-age axis, the earliest pull of any triggered pool is at launch+147, and hold 30 lands no later than launch+134: a margin of +13.
- At max_blocks 400 there is no such floor: 68 of 185 pools land after launch+147.

**Landing jitter:** 1 block (+1 or +2 after the sell is sent, 8 real c1 sells). The tails are rare: one late feed block (+1), and one 11.5-s sequencer stall (127 blocks).

### probe ev

This is j07, 20,000 Monte Carlo runs. Each attempt draws a real pool outcome from the engine-exact replay of all triggered pools at max_blocks 100. On each fill, a hazard q is the chance the operator pulls before our sell lands. A pull costs −$5.02 (stake plus gas), and then the c1 halt stops the probe.

**Per attempt**
- +$0.066 per attempt, 88% fill rate, +$0.076 per fill.
- Leave-one-out: +$0.056 to +$0.067.
- Without the top 3 pools: +$0.041.

**Break-even**
- The break-even pull hazard is 1.47% per fill (2.6% in the holder regime).
- The data show 0 pulls in 74 fills, which only bounds the hazard below 4.0% (one-sided 95%). So statistics alone cannot show the probe is above break-even. The case rests on how the operator times its pulls (the margins above).

**Probe until 100 attempts (about 1.9 days) or the first pull**

| Scenario | Expected $ | Other detail |
|---|---|---|
| q 0% (as in all data) | +6.61 | p5 +3.80, p95 +9.68 |
| q 0.5% | +3.51 | — |
| q 1% | +1.43 | — |
| q 2% | −1.15 | — |
| q 3% | −2.40 | — |
| q 5% | −3.55 | — |
| q 10% | −4.35 | — |
| Operator adapts at once | −5.02 | — |
| Adapts after 10 of our fills | −4.27 | — |
| Adapts after 25 fills | −3.15 | — |
| Adapts after 50 fills | −1.26 | — |

The floor is about −$5.1: one stake plus a few cents of flat losses. The ceiling is about +$10.

**How likely the operator is to adapt**
- It already reacts: it stops the router and pulls 36 to 175 blocks after a holder buys, and it has done so since at least Oct 11 13:44.
- Its pulls so far follow the pool's age, never before launch+147 in a triggered pool. They never came within 75 blocks of a holder's buy in a pool whose trigger was at or before T+100.
- It iterates on its launches. At 14:00 it switched to a new launch price, then went back to the line's shape at 14:37, 14:41 and 14:42.
- A faster pull is technically trivial: other operators on this chain pull within 3-13 blocks.

I put the chance that it moves its pull inside 32 blocks of our buy during the probe at roughly 30-50%. A mixture of "no adaptation" with that chance of adaptation at a random point gives about +$1.5 to +$3 of expected value, with the downside capped at one stake.

A dry run cannot measure this: a dry position is not in the pool, so the operator never reacts to it.

### new shape

The 14:00 shape (sqrtP 835109957917073511657837871095390, L 94871533698238694366969) comes from the same operator and the same router. Its pools behave differently, in a small sample, so do not add it. (j00 fetch, j05.)

**Count.** There are 7 such launches: 14:06, 14:12, 14:18, 14:21, 14:24, 14:27 and 14:39. The line's own shape came back at 14:37, 14:41 and 14:42.

**Why it is the same operator**
- It is the same 2,276-byte PositionManager multicall (ac9650d8), with the same layout. Only the token, the launch wallet, the price and amount words, the deadlines and the signature words differ.
- L × sqrtP is unchanged, so it deposits the same token amount at a launch price about 10% lower.
- The launch wallets are fresh (nonce 2-3), as on the line.
- Every pull was made by the pool's own launch wallet through the PositionManager.
- The router is 0xd6d35b56 with e6cb474f in every buy.
- Its router wallets overlap the ones seen before 14:14: 57/57, 39/43, 36/53, 19/31, 20/37, 13/33 and 16/37.
- The same dust bots (0xe71a69f4, 0xd2b94182) buy by launch+10.

**How its pools differ**

| Measure | 14:00 shape | Line, Oct 12 07:00-14:54 |
|---|---|---|
| Trigger, median | T+165 (31-268) | T+106 |
| Router ETH from T to T+60, median | 0.13 ETH | 0.66 ETH |
| Pulls | launch+1,228 to +6,261, one unpulled | — |
| Outside holders | none | — |

**Engine-exact replay as if it were armed**
- max_blocks 400: 7 attempts, 7 fills; hold 30 was flat in 6 and +7.8% in one. +$0.044 per attempt [−0.012, +0.157].
- max_blocks 100: 2 attempts, both flat.

**Arming it** would need pin false, which would admit any new fingerprint, or a code change. Neither is worth it for this probe.

### reasons

1. **The fill model is settled in skeptic 2's favour.** My independent replay reproduces all 8 of our real attempts: 5 fills exactly, and 3 minOut reverts with the right shortfalls. The engine fires inside the trigger transaction and quotes minOut from a copy that has not seen later buys in block T. So 0xcf1d880b, whose pull at T+19 behind the analyst's "every exit of 15+ pulled", is a revert. Under the engine's own fills, no exit landing at or before buy+32 is pulled: 0 of 23 holder-regime fills and 0 of 136 in all.

2. **Both verdict conditions hold.**
   - Hold 30 earns +$0.117 per attempt [+0.028, +0.228] in the holder regime and +$0.074 [+0.047, +0.105] in all triggered pools at max_blocks 400. At max_blocks 100 it earns +$0.066 [+0.031, +0.108] in all triggered pools.
   - It lands at buy+31 to +32. That is 4 blocks before the fastest reaction seen (36 blocks, against our own position in 0xb47b706f). Our real sells landed 1-2 blocks after being sent, so the margin is at least the jitter.

3. **Why max_blocks 100 rather than the box's 400.** At 400 the margin is real but thin, and it depends on luck in late-trigger pools.
   - With a trigger after T+113, hold 30 lands past launch+147, the earliest pull age of any triggered pool.
   - 0xcf1d880b (T 194, an outsider holding since before T) was pulled 17 blocks after our would-be entry. Only the minOut revert avoided it.
   - At 100, no traded pool was ever pulled before our buy + 84. Our own 4 fills with T ≤ 100 were pulled 84-115 blocks after our buy. The reaction lags seen in these pools are at least 75, and the age margin is 13 blocks.
   - The cost is about half the trades (about 54 a day against about 118). Also, the holder-regime interval at max_blocks 100 touches zero: −$0.002 at $5, n = 14, carried by 3 pools. It is above zero at $13 [+0.013, +0.824]. All triggered pools, which is what the probe actually trades, are clearly above zero.

4. **Where the others go wrong, and where they are right.**
   - The analyst's "no exit beats the reaction" rests on a fill the engine would not make.
   - Skeptic 1's take-profit with cap 40 fails the margin: when no take-profit fires, it sells at the cap and lands at +42, past the 36-block pull.
   - Skeptic 1 is right that the samples cannot bound the pull rate. Break-even is 1.5% per fill against an upper bound of 4.0% from 0 of 74. So only a live position can test the reaction. A dry run cannot, because the operator never sees a dry position.

5. **The probe is cheap to be wrong about.** The c1 halt stops trading at the first pull before our sell. The worst case is about −$5.1. With no adaptation the expected gain is +$6.6. If the operator adapts with a 30-50% chance, the expected value is about +$1.5 to +$3. The operator demonstrably changes its launches within hours and could pull faster at any time, which is why the probe stops at 100 attempts or the first pull, whichever comes first.

6. **Scope of this work.** Nothing was edited in src/, deploy/, tests/ or docs/, and nothing was committed. 45 read-only POSTs went to the public RPC through the paced ../../rpc.py. Scripts, outputs and caches are in /home/user/v2pons/research/session_oct12/c1/short/judge1/ (jc.py, j00 to j08 .py and .out, j01_pools.json, rpc_log.jsonl).

## Judge 2: LIVE PROBE

### settings

Change only the c1 object in FRONT_FAMILIES: "hold_blocks":30, "take_profit":9 (off), "stake_eth":0.002 ($5 at $2,500), "dry_run":false, "pin":true, "nonbot_halt":0. Trigger: router 0xd6d35b56…, selector e6cb474f, value_word 2, token_word 8, flag_word 7, flag_value 0, min_eth 0.005, max_eth 10, and "max_blocks":100 (it is 400 on the box today). Keep sqrt_p 792280926924313289846529216293289 and liq 100000088127620690885293.

Do NOT add the 14:00 shape: keep "pin" true.

Remove HALTED.front.c1 to start. Stop after 100 attempts, or at the first pull at or before our sell. That pull writes HALTED.front.c1 by itself (_settle, line 2008).

Front families have no near-miss halt; the near-miss rule at line 2011 covers follow only. So stop by hand if any c1 trade_done shows pull_after_buy_blocks <= 40.

Keep FRONT_DAILY_STOP_USD well above $5 (it is 100 on the box). Edit the JSON carefully: a mistake in a v4 family drops the whole list.

### fill model

From src/flip_engine.py:
- **Arming:** with pin true, a launch is armed only if its fingerprint matches the family's (arm_front, line 1231).
- **Trigger:** the first value-0 router buy call whose calldata word 2 is at least 0.005 ETH. It fires in its own block only when its launch offset is <= max_blocks (on_wave_call, line 2590).
- **minOut:** int(buy_out_int(copy, L, stake, 100) × 0.97). The copy is the launch sqrtP with every buy the feed shows applied: router calls by their calldata amount, strangers' ETH-value transactions that carry the token by their value, and never sells (_fire, lines 1685-1686). Our buy lands at the top of T+2 (7 of 8 attempts; one landed at T+7) and reverts if it gets fewer tokens than minOut.
- **Hold and sell:** hold counts from the block where the feed shows our buy (B). The sell is sent after the feed shows block B+hold and lands at B+hold+1 (once) or +2 (six times). The wall-clock fallback is 0.5 + 0.11 × (hold − 2) s after the fire.
- **take_profit:** checked on the copy at every buy behind ours.
- **Pull:** a pull at or before our sell (by block and index) writes the family halt.
- **nonbot_halt 0:** the streak halt is off for c1 (line 2020).

My own rebuild (j01) reproduces the on-chain minOut word of all 8 real attempts to the wei, and the token amounts of all 5 fills to within 1e-20. The 3 reverts fell 3.70%, 0.87% and 3.56% short of minOut. That is the same as skeptic 2's 6.59/3.84/6.45%, which were measured against the quote before the 3% slip.

So skeptic 2's model matches our 8 attempts. Two small corrections:
- 0x35869115 actually landed at T+7, index 6. It reverts either way.
- Our real sell lag is 1-2 blocks, against skeptic 2's 1/2/3 mix, so their mix is a little pessimistic.

The analyst filled 7 regime buys that the engine reverts. One is 0xcf1d880b: 2.4% short of minOut after a 0.28 ETH router buy in block T. That pool was the whole basis of "every exit of 15 blocks or more is pulled".

### cells

Engine-exact replay (j02/j03): $ per attempt at $5, with reverts and real gas. Base scenario is a T+2 buy with sell lag 2; "mix" is the observed landing distribution. 95% pool-bootstrap CIs.

**max_blocks 400, holder regime** (n 30 attempts, 23 fills):

| Exit | $ per attempt [CI] | Mix | Pulled |
|---|---|---|---|
| hold 20 | +0.042 [+0.002, +0.093] | | 0 |
| hold 25 | +0.062 [+0.004, +0.138] | | 0 |
| hold 30 | +0.117 [+0.029, +0.227] | +0.089 [+0.026, +0.168] | 0 |
| hold 35 | -0.057 [-0.44, +0.18] | | 1 (0xb47b706f at buy+36) |
| tp 4% cap 30 | +0.060 [+0.016, +0.112] | | 0 |
| tp 6% cap 30 | +0.085 [+0.023, +0.164] | | 0 |
| tp 4% cap 40 | +0.104 [+0.053, +0.162] | | 0 |
| tp 6% cap 40 | +0.129 [+0.061, +0.208] | | 0 |
| hold 60 | -0.073 | | 2 |

**max_blocks 400, all triggered** (n 182, 134 fills):

| Exit | $ per attempt [CI] | Pulled |
|---|---|---|
| hold 20 | +0.040 [+0.022, +0.059] | 0 |
| hold 25 | +0.051 [+0.031, +0.074] | 0 |
| hold 30 | +0.076 [+0.048, +0.106] | 0 |
| hold 35 | +0.058 [-0.013, +0.110] | 1 |
| tp 4% cap 30 | +0.056 | 0 |
| tp 6% cap 30 | +0.067 | 0 |
| tp 4% cap 40 | +0.087 | 0 |
| tp 6% cap 40 | +0.100 | 0 |

**max_blocks 100, holder regime** (n 14, 14 fills, 0 pulled at every exit):

| Exit | $ per attempt [CI] | Mix |
|---|---|---|
| hold 20 | +0.046 [-0.011, +0.120] | |
| hold 25 | +0.086 [-0.011, +0.235] | |
| hold 30 | +0.132 [-0.002, +0.311] | +0.121 [+0.004, +0.276] |
| hold 35 | +0.165 [+0.027, +0.334] | |
| tp 4% cap 30 | +0.060 [-0.002, +0.136] | |
| tp 6% cap 30 | +0.100 | |
| tp 4% cap 40 | +0.130 [+0.052, +0.211] | |
| tp 6% cap 40 | +0.170 | |

**max_blocks 100, all triggered** (n 83, 73 fills, 0 pulled):

| Exit | $ per attempt [CI] |
|---|---|
| hold 20 | +0.039 [+0.014, +0.068] |
| hold 25 | +0.050 [+0.020, +0.086] |
| hold 30 | +0.067 [+0.032, +0.110] (mix +0.065 [+0.032, +0.104]) |
| hold 35 | +0.076 |
| tp 4% cap 30 | +0.047 |
| tp 6% cap 30 | +0.062 |
| tp 4% cap 40 | +0.077 |
| tp 6% cap 40 | +0.095 |

Robustness of hold 30 in the holder regime:
- At 400: leave-one-out +0.065 to +0.092; without the 3 best pools +0.028.
- At 100: without the 3 best pools +0.001, so it rests on a few winners.

**Margins: landing measured from our buy.**
- Landing: hold 20 at +21..23, 25 at +26..28, 30 at +31..33, 35 at +36..38; cap 30 by +33, cap 40 by +43.
- Known reaction pulls on positions bought by T+150 (24): 36 (ours, T 155), 45, 54 (0xbd9dc5f6, T 148/150), 65, 72, 74, 75, 75, 80, 84, 97 and 115 (ours) and later.
- Margin to the fastest (36): hold 20 +13..15, hold 25 +8..10, hold 30 +3..5. Hold 35 is hit, and cap 40 sits 5-7 blocks past it.
- In pools with T <= 100 the fastest reaction is 75 (outsider) or 84 (ours), so hold 30 has 42-53 blocks.
- Pool-age clock: at max_blocks 100 the sell lands by launch+134..136. The earliest pull of any triggered pool was at launch+147.
- Replay, pull minus landing for hold 30: smallest 4 blocks at max_blocks 400 (0xb47b706f) and 52 at max_blocks 100.
- All three early pulls sit in pools with T over 100: T+19 at T 194, T+38 at T 155, T+63 at T 103.
- Landing jitter: about 1 block. Our 7 c1 sells landed 1 block after sending once and 2 blocks six times. 130 of 132 front sells landed 1 block after sending. In more than 1,000 live sells there was one 1-block feed delay and one 11.5 s stall (about 110 blocks).

### probe ev

Probe at hold 30, $5, max_blocks 100, run until 100 attempts or the first pull inside the hold. Expected $ = E[N] × E[$ per attempt] (Wald), checked with a Monte Carlo (j07, j09).
- **With no pull inside the hold** (what the replay saw): +$6.5 over all triggered pools, +$12.2 in the holder regime.
- **Break-even hazard** (chance per fill of a pull inside the hold): 1.5% (all) and 2.4% (holder).
- **Fitted hazard:** a lognormal on the reaction lags in T <= 100 pools (75, 80, 84, 91, 97, 115…), times the 4/5 chance that a reaction comes at all, gives 0.8% per fill. At that hazard:
  - expected +$2.2 (all) / +$5.8 (holder);
  - chance of a net loss 0.28-0.41; 5% quantile -$4.8.
- **At a 3% hazard:** -$1.0 to -$2.4.
- **Worst case:** about -$5.07, one stake plus gas, capped by the family halt.
- **Same probe at max_blocks 400:** the fitted hazard is about 2.8%, because the fast reactions (36, 45, 54, and the T+19/T+63 cases) all sit in T > 100 pools. Expected -$0.9 to -$1.5, chance of a loss 0.71-0.77. That is why I recommend 100.
- **Adaptation:** if the operator starts pulling inside 30 blocks after K of our exits, the probe ends at about -$4.3 (K 10), -$3.7 (K 20), -$2.6 (K 40).
- **How likely adaptation is:** likely, roughly even odds within the probe.
  - It already watches holders and pulls 36-175 blocks after their buy.
  - It changed its launch shape at 14:06, and has run both shapes alternately since 14:37.
  - A faster pull is a single PositionManager transaction.
- **Duration:** about 53 triggers a day have T <= 100, so 100 attempts take about 2 days.

### new shape

There are now 7 launches of the new shape (sqrtP 835109957917073511657837871095390, L 94871533698238694366969), from 14:06 to 14:40 UTC. Two are in the analyst's cache; I fetched 5 more up to the 14:58 head (j04, 34 POSTs, 10 HTTP 429s).

**Same operator and router.**
- Each launch is the same 2,276-byte value-0 PositionManager call, from a fresh launch wallet (nonce 2-3).
- Every pull was made by the pool's own launch wallet.
- The buys go through router 0xd6d35b56: 92 of the 129 router EOAs were already seen before 14:14.
- The same dust and recurring bots are present: 0xe71a69f4, 0x97ac054b, 0xd2b94182, 0x5e6ec144, 0x3155c72d.

**The pools behave like old-shape pools with no holder.**
- Pulls came at T+1,062 to T+6,230; one pool is still live.
- The router made 33-62 buys and 4-22 sells per pool.
- In 4 of 7 pools the only router buying by T+60 was the trigger itself (0.008-0.018 ETH).
- No outsider held 0.001 ETH or more before T+62, so the reaction to a holder is untested on this shape.

**Engine-exact replay, as if armed:** hold 30 made +7.8% in 1 of 7 pools and was flat in the other 6, about +1.1% on average. That is weaker than the old shape.

The old shape came back at 14:37 (3 launches by 14:42), so the probe still has launches.

Trading the new shape would need "pin": false. A family holds only one sqrt_p/liq, and a second family with launch value 0 is refused. With the pin off, the family would also arm any future fingerprint unseen. Verdict: do not add it.

### reasons

1. The engine-exact fill model is confirmed. My own rebuild reproduces all 8 real buy attempts exactly: the minOut word, the 5 fills and the 3 reverts. Skeptic 2 is right that the analyst filled buys the engine reverts, 0xcf1d880b (T+19 pull) among them. Without that pool, no exit landing at or before buy+33 is pulled: 0 of 23 regime fills, 0 of 134 overall.

2. Condition 1 holds for hold 30. Its $ per attempt is positive with a CI above zero:
   - max_blocks 400: +$0.117 [+0.029, +0.227] in the holder regime, +$0.076 [+0.048, +0.106] over all triggered pools.
   - max_blocks 100: +$0.065 [+0.032, +0.104] over all triggered pools, and +$0.121 [+0.004, +0.276] in the holder regime under the measured landing mix.
   - Caveat: at max_blocks 100 the holder regime has n 14, and its base-scenario lower bound is -$0.002.

3. Condition 2 holds. Hold 30 lands at buy+31..33, which is 3-5 blocks before the fastest reaction ever seen (36). The normal landing jitter is 1 block. With max_blocks 100 there is much more room: the fastest reaction in those pools is 75-84 blocks, the sell lands 13 blocks before the earliest pull of any triggered pool (launch+147), and the smallest pull-to-landing distance in the replay is 52 blocks. All three early pulls were in pools with T over 100.

4. The downside is capped. The family halt limits a probe to about one $5 stake plus gas. The probe's expected $ is roughly +$2 to +$6 at the fitted 0.8% hazard, and negative if the operator adapts.

5. Why not the alternatives:
   - Hold 35 and take-profit with cap 40 land past the 36-block reaction.
   - Take-profit with cap 30 earns less than plain hold 30.
   - Hold 25 at max_blocks 100 fails condition 1 in the holder regime (CI down to -$0.011).
   - Hold 60 stays bad in the holder regime.

6. Caveats, none of which change the verdict:
   - The zero-pull count cannot bound the hazard below break-even: 0 of 23 has a 12% upper bound against a 2% break-even.
   - The 11.5 s sequencer stall seen once in about 1,000 sells would overrun any margin.
   - Adaptation is likely.
   So treat this as a capped experiment, not a scale-up.

Files are in /home/user/v2pons/research/session_oct12/c1/short/judge2/: j01_engine, j02_sim, j03_tables, j04_shape (RPC), j05_shape_cmp, j06_margin, j07_probe, j08_grid, j09_hazard (.py and .out), plus jc.py and rpc_log.jsonl. Nothing in src/, deploy/, tests/ or docs/ was edited, and nothing was committed.
