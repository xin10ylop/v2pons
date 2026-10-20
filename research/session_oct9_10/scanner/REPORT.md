# SCANNER RESULT (workflow wf_bb5f0c95-4a1)

## report object


### report_markdown

I did not finish this report and I am not continuing it. A safety check stopped my response partway through, so the report, the ranked list and the engine requirements are not here. Do not treat this output as a finding. The empty candidate list does not mean "none today", and method_valid=false does not mean the controls failed. Neither was assessed.

### candidates

[]

### method_valid

false


## ranked

{"key": "CODEHASH:f07d1c5394b19c29a66c743b88203c903d43913ae90ca1292462955c4cc28a57|e1e75b94|5572|2500|25|false", "score": 815, "verdict": "candidate"}
{"key": "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|10000|200|true", "score": 456.49, "verdict": "candidate"}
{"key": "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2276|100|1|true", "score": 158, "verdict": "candidate"}
{"key": "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|true", "score": 103.57, "verdict": "candidate"}
{"key": "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true", "score": 77.61, "verdict": "candidate"}
{"key": "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|500|10|true", "score": 22.77, "verdict": "candidate"}
{"key": "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|500|10|true", "score": 22.77, "verdict": "candidate"}


## judged (full)


### CODEHASH:f07d1c5394b19c29a66c743b88203c903d43913ae90ca1292462955c4cc28a57|e1e75b94|5572|2500|25|false
real_candidate=False confidence=medium


**identity**
One operator, and not operator A or the volume bot. Same operator throughout: one buyer wallet 0x9fdd8cea (nonce ~12.8k on Oct 7; it shows up in ops2/dep4cd.json and origins/relay_deposits_83280000_83500000.json only as a small Relay-bridge depositor, 0.005-0.0066 ETH, unlabelled) buys every pool. The launch wallet and the buyer each burn their token holdings to 0xdead in the blocks right after every pull. The buyer's nonces are perfectly interleaved, one buy and one burn per launch. Each next deployer creates its launch contract and then deploys its hook through the CREATE2 proxy 0x4e59b448, a few seconds before its launch. Not operator A: no 0x3194e326 launcher, no 2fcb9108 or 2793923d copies, no 1,124-byte crowd buys, and 0x9fdd8cea is not in money/loop.json 'crowd'. A's cash-outs also reach Base via 0x487cab40, while this money stays in 100 Robinhood wallets. Not the volume bot: no 0x1cbaf24d router, no 2.4333285-ETH POSM multicall, no decoys (0x65050a9b, 0x93b07902), and its pulls go through the router while these go through the POSM. Notably, the chain-wide dust bot 0xe71a69f4 is absent from 0/102 pools, although it buys nearly everything else. That is consistent with either 'unrecognised launch path' or 'blocked by the hook/token', and the census cannot tell the two apart because it has no receipts of reverted attempts.


**recomputed**
From the census raw data (scripts and caches in /tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/skeptic_CODEHASH_f07d1c5394b19c29a66c743b88203c9/: s0_load.py, s2_stats.py, s3_minout.py, s4_between.py, s5_links.py, s6_bal.py, s7_code.py; outputs rows.json, minout.json, balances_now.json). COUNT: 102 pools confirmed. Every pool has the same value (50018847145969 wei), sqrt (2506289003612544606728200307581467, tick0 207250), one range (69075,207250) and liq 31643365286403255465701. There are 100 deployers (0x35eb8c43 launched 3), launching at nonce 2 (77), 6 (22), or 3/9/10. All 102 hooks have the same 937-byte code. Each token is 2,530 bytes with its own code hash. TIMING: the per-day rate is not real. The family is 2 pools at 16:41-16:48 UTC with no buy, then a 45-minute gap, then all 100 traded pools inside 23 minutes (17:33:21-17:56:05 UTC Oct 10). Median gap between launches is 13 s. '51/day' is that one 23-minute burst averaged over 48 h. FIRST BUY: exactly 1 swap in each of 100 pools, all by 0x9fdd8cea through the Universal Router, never a sell. Offset from launch +14/15/16 (p10/50/90), with 15 in 41 pools, 16 in 26, 14 in 18 and 12-24 in the rest. Sizes 0.0713/0.3167/1.0112 ETH (min 0.0617, max 2.01). They come in descending tiers in launch order: 2.01 x8, then 1.01 x12, then 0.51 x15, then ~0.32 x22, then 0.06-0.18, creeping up about 0.0002 ETH inside each tier. This looks like a scripted one-off sequence, not a market-driven schedule. PULL: 100/100 by the launch wallet through the POSM (dd46508f, BURN + TAKE_PAIR to the launch wallet itself). Pull at +29/30/32 after launch and +14/15/16 after the buy (53 exactly +15, 19 at +16, 17 at +14). The 2 unbought pools were never pulled. MINOUT (the analyst said it could not be decoded; it can): execute(commands 0x10 V4_SWAP + 0x04 SWEEP), actions 06 0c 0e (SWAP_EXACT_IN_SINGLE, SETTLE_ALL, TAKE). amountOutMinimum is exactly 0.95 x the launch-state quote in 100/100 (not 0.99), and the actual output equals the quote. Exact room ahead before the scheduled buy reverts is 0.0268/0.0269/0.0296/0.0348/0.0392 ETH (min/p10/p50/p90/max). So 0/100 revert at 0.0058 ETH. The analyst's 'honest' case (65/102 revert, median -0.57%) and the '$10 operating point' are both wrong. With 5% slack the $15 stake is well inside capacity, and the analyst's naive numbers (+132% mean / +71% median / 96% win) are the relevant ones. I did not re-run the return replay myself, so those return figures remain the analyst's.


**strongest_objection**
This is not a recurring operator. It looks like a one-time movement of about 48 ETH from one wallet into 100 fresh wallets, done through throwaway tokens. Evidence: (1) The buyer's nonce rises by exactly 2 between consecutive buys (12919..13117, 99/99 steps). Between buys, both the launch wallet and the buyer send their tokens to 0x...dead right after the pull, for example in block 85176421/85176435: 332,522,448,376,259,643,220,205,470 + 667,477,551,623,740,356,779,794,527 = exactly 1e27, the whole supply. So each cycle is: create token, launch, buy X ETH, pull X ETH to the launch wallet, burn the whole supply. (2) The ETH did not come back. At head 85,315,143 the 100 launch wallets hold 48.54 ETH (the 2.01-ETH tier wallets about 2.0 each) and the buyer holds 4.17 ETH. Nothing was refilled, so it is a one-way distribution, not a pot that loops like operator A's. (3) The launch wallets have kept going on other contracts: they are now at nonces 9-21, and 0x35eb8c43 launched a different family (0x6765bede, selector 82a55dde, 1252 bytes, code hash adb26f86) at block 85195867, 18:07 UTC. Nothing of this code hash appears after 17:56 in the census. A 23-minute burst that empties its funding wallet does not give ~300 trades a day the way the volume bot does. (4) Our profit would come straight out of the operator's own ETH, which only the pull recovers, so any recurrence would likely react. (5) The hook is not proven swap-neutral at launch time. Its bytecode reads tx.origin and makes an external staticcall. The analyst's beforeSwap eth_call ran at latest state, long after the window, so it does not show that a buy from our wallet at launch+1 would pass. That remains unverified. I am not taking the hook analysis further here.


**live_test**
Watch-only first; no stake until the family recurs. (A) Recogniser, logging only: a tx whose target has code hash f07d1c53..., selector e1e75b94, calldata 5572 bytes, value 50018847145969 wei, initializing a fee 2500 / ts 25 pool with the 937-byte hook and sqrt 2506289003612544606728200307581467. Also log the sibling 0x6765bede/82a55dde family and any launch whose sender belongs to the 100 deployers listed in g3_raw.json, since the operator changes contracts. Run for 7 days. Pass to stage B only if it shows at least 3 separate bursts on at least 2 different days with at least 150 launches in total, buys by one wallet at launch +12..+20 in at least 95%, minOut still at or below 0.95 x the launch quote (decode word 26 of the SWAP_EXACT_IN_SINGLE params), and the pull at least 12 blocks after the buy in at least 98%. (B) FRONT_DRY_RUN over at least 100 recognised launches: fire at launch, land at +1, exit on the first Universal Router buy from the scheduled wallet behind ours, or launch+20 as the deadline. Before any live stake, confirm with a full simulation from our own relay at the launch block (pending state) that both the buy and the sell succeed. Pass: at least 95% of simulated buys and sells succeed, 0 pulls at or before our sell, median priced return at least +20% after two fees and gas. (C) Live at 0.0058 ETH for 30 trades with the existing per-strategy halt. Any pull at or before the sell, or a pull margin shrinking below +10 after our buy, stops it.


### 0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|10000|200|true
real_candidate=True confidence=medium


**identity**
It is the known volume bot in another shape, not operator A and not a new operator.

Shared with the volume bot:
- The scheduled buyer and the puller are the same router, 0x1cbaf24d. It buys with c1120e3d from 110 (v3.0) and 100 (v5.0) reused wallets.
- Each pool is pulled by its own launch wallet via a0f7978d, full, in 511 of 511 pulls.
- The launch template matches v2.433: POSM multicall, 1,444 bytes.
- HANDOFF section 1 already names 3.0 ETH and 5.0 ETH at fee 1% as the bot's untraded families.

Weaker links than the claim assumes:
- The router is a public launch-bundler contract: anyone can call its buy (eth_call from an unrelated address succeeded). Its contract nonce is 33,056 and its strings include 'snipers length mismatch', 'holders length mismatch' and 'liquidity too low'. Sharing it proves the tool, not the owner.
- No wallets are shared with v2.433: 0 of its 31 bot wallets and 0 of its 1,843 launch wallets appear here.
- v3.0 co-bursts more with v5.0 (66% of active 2-minute buckets) than with v2.433 (47%).
- v3.0 and v5.0 kept launching (45 and 23 launches since) after v2.433 went silent at 19:28 UTC. That is 2 h 7 min, against a 48-h maximum gap of 7 minutes.

The operator link: v5.0 carries v2.433's decoy setup. 0x488faf52, the decoy funder, buys directly in 16 v5.0 pools, and the decoy router 0x65050a9b appears in 215.

Operator A: zero overlap with its 145 addresses in money/loop.json, and its launcher 0x3194e326 / 2fcb9108 is never used. Launch-wallet funders cannot be checked over this RPC (no traces or indexer).


**recomputed**
I recomputed everything from census/ raw rows with my own code (scripts s1-s9 in skeptic_0x58daec3116aae6d93017baaea7749052e8a04f/), across the whole family plus a seeded random sample of 300 per sub-family. I also fetched 3.25 h of fresh data past the census (blocks 85,203,898-85,316,120, to 21:35 UTC Oct 10).

COUNT: 1,339 = 889 v3.0 (value exactly 3e18; one sqrtP 679394651928963067279918579724198; L 25725498245903809899643; one add each) + 434 v5.0 (5e18; sqrtP 526364174002223567019744861584709; L 33218249502344340119344) + 16 others (value 0 or 1e-6, different sqrtP, L 0, no bot). The 16 are not the bot and must be excluded. Every launch has a distinct wallet. v3.0: nonce 3 in 458, 257-268 in the rest. v5.0: nonce 223-238. Fresh 3.25 h: 69 v3.0 and 37 v5.0 (about 510 and 270 a day), still launching at 21:28 UTC.

BOT BUY (router 0x1cbaf24d, c1120e3d): present in 889/889 v3.0 and 434/434 v5.0 pools, and 69/69 and 37/37 fresh.
- v3.0 offset histogram: +6:5, +7:45, +8:313, +9:292, +10:164, +11..17: 60, later than +20: 7 (max +179). So +6..+10 = 92% (the claim says 94%).
- v5.0 offset: +7..+10 in 91%.
- Size: v3.0 min/p10/p50/p90/max 0.0495/0.074/0.124/0.174/0.236 ETH; v5.0 min 0.02475.
- minOut (word 4) / buy_out_int(launch state) = 0.949999-0.95 in all 1,323 pools and in all 106 fresh ones.
- Calldata words: 0 UR, 1 PM, 2 token, 3 = L0/4 (a 'liquidity too low' guard), 4 minOut, 5 recipient = the bot wallet, 6 deadline, 7 fee, 8 tick spacing, 9 hooks.

PULL: 342 of 889 v3.0 (38.5%) and 169 of 434 v5.0 pulled within 3,000 blocks. Every one was full, by the launch wallet, through router a0f7978d. None came before or in the block of the bot's buy. v3.0 pull minus bot p0/10/50/90 = 3/21/443/2300. Fresh v3.0 minimum = bot+21.

TRAP: 24 pools had a non-operator buy ahead of the bot (21 v3.0, 3 v5.0). The bot still bought on schedule in all 24. 23 were pulled at bot+3 (11), +4 (2) or +8..+11 (10); one 1.98e-5 buy drew no reaction (pulled at bot+185). The reaction is gated on the bot's buy: in pool 0x94f7fc45 the outsider bought at +2, the bot at +14, and the pull came at +17. The reaction tightened over time: the Oct 9 16:48 burst pulled at bot+8..10, the Oct 10 04:38 burst at bot+3 in 8 of 11. None of the three outsiders (0xfeda1c58, 0x9a128676, 0x9f3b9a44) ever sold; all were rugged. So nobody has ever actually sold into this family's bot buy.

FRONT REPLAY: our buy inserted after block +1, every later swap replayed by its own shift, bot buys under their minOut dropped, sell at the head of bot+1, gas 207,755 x base fee.
- v3.0 at 0.0058 ETH: n 889, mean +6.03%, median +6.09%, win 99.2%, 0 pulled first, 7 deadline exits at -2.07%, $0.90 a trade, $402 a day. Random 300: +6.18%. Every 6-h slice +5.6% to +6.7%.
- Same result landing at +2 or selling at bot+2. Selling at bot+3 gives 8 pulled-first in history, and about 46% if we are the outsider in every pool.
- Stake curve: flat +6.0% from 0.0029 to 0.075 ETH (1 bot buy dropped). At 0.08 ETH, 343 bot buys revert (+3.8%); at 0.1 ETH, 882 revert (-1.96%). Bot-buy fill ratio with our 0.0058 ahead: 1.042-1.049.
- v5.0: +1.75% mean, +1.81% median, 87% win, $0.26 a trade, $57 a day.
- Fresh 3.25 h: v3.0 +5.83% mean, +6.08% median, 98.6% win (n 69); v5.0 +1.62%. Ahead of the bot in the fresh pools: only the 2e-6 dust bot, no decoys.

The claim's numbers survive; only small details are off (the 94% figure, and 25 deadline exits that include the 16 non-bot pools).


**strongest_objection**
This is not a new operator. It is the volume bot's own documented second line: HANDOFF section 1 already lists v3.0 and v5.0. It runs through the same router, with the same buy, the same pull call, and a trap pull at bot+3 after any outsider. So it carries the adversary that took most of v2.433's margin with decoys within about 6 hours. On v2.433 those decoys were still running at 21:30, long after our engine stopped. Only v2.433 had decoys ahead of the bot's buy; v3.0's fresh pools still have none. If we start trading it, expect the same response here.

Every exit is fakeable at gas cost:
- The router's buy is callable by anyone (my eth_call from 0x...dead1 succeeded on live v3.0 pools).
- The feed shows reverting transactions, so a tiny or reverting c1120e3d triggers our sell-on-bot rule.
- In this 1% fee tier each forced exit costs about -2.1%, against -0.6% on v2.433.

The trap margin is already at its floor: the pull came at bot+3 in 8 of the 11 latest trap pools (Oct 10 04:38), down from bot+8..10 on Oct 9. A one-block slip in our sell is survivable; two blocks lose the stake about half the time.

Nobody has ever sold into this bot's buy. The three 'competing front bots' all held and were rugged, so the operator's response to a profitable seller is unobserved. The break-even is lenient: about 26% of trades need the real bot buy to fill. That is why this is a downgrade to 'conditional', not a refutation.

Separately, the box's feed is blocked (HANDOFF 16.11), so nothing can run without an authorized feed provider.


**live_test**
Prerequisite: an authorized feed and RPC provider (HANDOFF 16.11). The box must not reconnect to the public feed.

RECOGNIZER (v3.0 only; v5.0 is too thin at +1.75%):
- Transaction to POSM 0x58daec3116aae6d93017baaea7749052e8a04fa7, selector ac9650d8, 1,444 bytes, value exactly 3000000000000000000 wei.
- decode_launch must give currency0 0, fee 10000, tick spacing 200, hooks 0, sqrtP 679394651928963067279918579724198 and MINT liquidity 25725498245903809899643.
- Pin sqrtP and L so the 16 value-0 pools and any look-alikes are rejected.

FIRE: at the end of the launch's feed block, landing at +1. Skip the pool if a 0x1cbaf24d buy has already been seen, or if more than 0.07 ETH sits ahead including our stake. Stake 0.0058.

EXIT:
- Sell at once on the first transaction to 0x1cbaf24d with c1120e3d whose word 2 is our token, landing at bot+1.
- Turn off the take-profit and size rules for this family. A fake large buy would force a -2% exit, and real moves are well above 3%.
- Deadline: send at +18, land by +20.
- Halt on the first pull at or before our sell, and after 5 consecutive non-bot or deadline exits (the fakes or decoys signal).

STAGE 1, dry run with FRONT_DRY_RUN (no buy), at least 200 v3.0 launches (about 10 h). Pass if all hold:
- At least 98% of chain-confirmed 3.0-ETH launches are recognized in the launch block.
- The bot's buy is seen at +6..+14 in at least 95%.
- minOut / launch quote = 0.95 in 100%.
- Non-us ETH ahead of the bot is 0.01 or less in at least 95%.
- The simulated sell block (bot+1) is before the pull in 100%.
- Replayed mean is +5% or better.

STAGE 2, live probe: needed because the trap only fires on a real buy. 50 launches at 0.002 ETH. Pass if all hold:
- 0 pulled first.
- At least 90% sold at bot+1, and the pull lands at least 2 blocks after our sell every time.
- The bot still buys in at least 95% of the pools we entered.
- Net mean +4% or better.
- No fake router buys and no decoys at 0.01 ETH or more ahead.

Then 200 trades at 0.0058 with the same criteria before calling it live. Share the one position slot with v2.433: only 19 of 889 v3.0 launches fell within 12 blocks of a v2.433 launch.


### 0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2276|100|1|true
real_candidate=True confidence=medium


**identity**
It is a third operator ("operator C"). It is not operator A and not the volume bot, but it has the self-funded structure the owner asked for: the "crowd" is its own buyer. The analyst's "crowd" label is correct in spirit but wrong in detail: there are at least 1,049 wallets, not 38 keepers.

**One loop, traced on the chain**
1. Creators forward their pulled ETH. All 8 of the largest pulls I traced (10.4-15.4 ETH each) were sent onward 82-403 blocks after the pull, to the 1,780-byte multisend contract 0xf341c935599822f1bc1ec29e27606724fbbf6595 (selector c76bd193, which takes address[] and uint256[]).
2. The multisend pays the next launcher. 7 of the 8 recipients are later launchers of this same family, each launching with nonce 3.
3. That launcher passes the ETH to a hub. Example: 0x0440d6cf received 14.38 ETH at block 84,326,064. At 84,326,143 (nonce 0) it sent 14.2 ETH to the hub EOA 0xbae538011874261e3fb4ca6aa03cacb2766c4d81 (nonce 3,067). It then deployed its token (nonce 1), approved it (nonce 2), launched pool 0xf7a2d60f (nonce 3), pulled it (nonce 4) and forwarded 14.49 ETH to the next launcher (nonce 5).
4. The hub funds the buying router. At 84,326,173 it sent 14.0 ETH to the router 0xd6d35b56. It also called the router's e7741137(0x834f3aa5…, 1).
5. The hub pays the crowd's gas. Through the same multisend it topped up gas for 965 wallets, and 965 of those 968 recipients are known router wallets.

So the launcher, the crowd router and the pull are one self-funded machine. The router held 76.5 ETH at my last read.

**What it is not**
- The router's crowd sells as well as buys (1,691 sells). It looks like wash trading made to resemble organic volume.
- No address in this family overlaps the 152 known addresses in docs/HANDOFF.md and research/session_oct9_10/money/loop.json: not the crowd wallets, launchers, pullers, hub, collector or router.
- Router 0xd6d35b56 trades only this family. Earlier research (others/crowd.json, "PM2276") also found it shares no wallets with operator A.
- The only overlaps are incidental. The chain-wide dust wallets 0xe71a69f4 and 0x93b07902 appear, and the volume bot's decoy router 0x65050a9b appears as a route used by unrelated outsiders (15 buys, 9 sells in 66 pools).


**recomputed**
The scripts and JSON outputs are in /tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/skeptic_0x58daec3116aae6d93017baaea7749052e8a04f/f2276_100/. That directory name is shared with other POSM families, so I worked in the subfolder f2276_100.

My sample has two parts:
- 60 seeded census pools, with every swap's transaction fetched (6,416 swaps, 0 missing). The census itself only has the first 8 swaps' transactions.
- Every family launch after the census, Oct 10 18:20-21:30 UTC, as an out-of-sample set: 6 launches with the same fingerprint, all fetched.

**COUNT**
- 245 launches over 47.4 h, which is 124 a day, but in bursts by 6-hour slice: 16/15/25/92/38/13/8/38.
- The post-census window had only 6 launches in 3.17 h, about 45 a day.
- 242 launches use sqrtP 792280926924313289846529216293289 with L 100000088127620690885293; 3 use 8.351e32 with L 9.487e22.
- Every launch has value 0 and range [-887272, 184216], mints 1e9 tokens, and comes from a fresh deployer (245 deployers, nonce 2 in 155 and nonce 3 in 90).
- All 66 tokens checked share one code template (3,854 bytes).

**FIRST BUY**
- The first buy through router 0xd6d35b56 appears in 203 of 245 pools. Of the rest, 40 pools never got it (8 or fewer swaps) and 2 are unknown.
- Offset from the launch, min/p10/p50/p90/max: +4 / +68 / +116 / +204 / +501. Size: 0.0002 / 0.012 / 0.13 / 0.29 / 0.644 ETH.
- The router is far bigger than the analyst says. In the 66 fully attributed pools it made 4,072 buys (652.7 ETH) and 1,691 sells (275.6 ETH back out). Outsiders bought only 0.255 ETH in total.
- At least 1,049 wallets use it in those 66 pools (4,400 across everything I fetched), not "38 keepers". 28 different wallets made the first buy in 56 pools.
- Every one of the 5,763 calls is signed the same way: gas limit 1,000,000 and gas price equal to the tip.
- Every call has minOut = 0 (calldata word 3). On buys the recipient (word 1) is the wallet itself; on sells it is the router.

**PULL**
- 151 of 245 pools (61.6%) were pulled within 3,000 blocks. Every pull was full, made by the launch wallet through POSM dd46508f.
- Offset from the launch, p10/50/90: 117 / 350 / 1913. From the first router buy, min/p10/50/90: 40 / 84 / 376 / 1917. No pool was pulled before that first buy.
- The pull comes after the router stops buying: from the last buy of 0.01 ETH or more to the pull, p10/50/90 is 8 / 48 / 174 blocks. The 40 pools the router never bought were pulled at +84 / +166 / +259.
- The creators took 447.8 ETH out at the pulls.

**RIDE**
This is my own single-range replay: buy 0.0058 ETH at the end of the block after the first router buy (c1+1), sell at the start of the block 50 later, the fee taken per swap, $0.012 of gas, and a pull at or before the sell counted as the whole stake lost.

| sample | n | mean | median | win | pulled |
|---|---|---|---|---|---|
| census 203 + fresh 6 | 209 | +11.5% | +5.7% | 69% | 5 |
| fully attributed pools | 56 | +11.3% | +3.0% | 62.5% | 0 |
| fresh, out of sample | 6 | +8.2% | +5.5% | 4 of 6 | 0 |

- The 209-pool set works out to $1.73 a trade. Its p10 is -0.1% and its p90 is +40.6%; without the top 5% of trades the mean is +7.6%.
- Landing later costs little: c1+2 gives +10.5% and c1+3 gives +10.0%.
- Shorter and longer holds: 20 blocks gives +6.8% mean but a -0.1% median; 100 blocks gives +21.9% but 16 pulled.
- A random entry between launch+30 and +300 with a 50-block hold gives +6.0% mean and a +0.3% median, so the trigger adds something.
- All eight 6-hour slices have a positive mean. Oct 9 06-12 UTC is flat: +1.2% mean, -0.1% median, 31% win.
- One wallet already rides these pools: 0x97ac054b, through router 0x897c3456, at 0.0002 ETH. In my 66 pools it made 52 rides, buying at c1+33 (median) and holding 40-60 blocks, for a realised +13.9% mean with 2 rides lost to pulls.

**FRONT RULE**
I did not re-run it. The first router buy is not at a fixed time, so selling ahead of it does not apply. The analyst's numbers for it are negative or flat anyway.


**strongest_objection**
The edge is a 50-block ride on a machine-run fake crowd, and that machine belongs to the operator whose money we would be taking. It is not a scheduled buy with slack and a fixed pull margin.

- Nothing anchors the timing or size of the router's buying. The returns depend on its bursts: median +5.7% against a +11.5% mean, 31% of rides lose, and 2.4% lose the whole stake to the creator's pull (which comes 40 or more blocks after the first router buy).
- The trap risk at our size has never been tested. No outsider has ever bought $15 at c1+1 in these pools.
- The data does show one worrying pattern. In 6 of 15 pools where an outsider bought 0.001 ETH or more among the first 8 swaps, the pool was pulled within 100 blocks. Matched control pools were pulled that fast only 12.3% of the time (binomial p about 0.006).
- Those pulls came 60-86 blocks after the outsider's buy, which is only 10-36 blocks after our planned sell. One case was 0.2277 ETH followed by a pull 70 blocks later. Read swap by swap, the six look like the normal pull after the operator's buying stops (40-105 blocks after its last buy, at +166 to +209 from the launch), not like a reaction. But the operator can tell its own wallets from outsiders, and it could start reacting.
- The launch rate in the 3 h after the census was about 45 a day, not 122.5.
- A 5-second hold ties up the engine's single position slot, which front uses for about 300 trades a day at about $2 each.


**live_test**
**1. Dry run (no trades), at least 100 triggered launches, about 1-2 days at 45-120 launches a day.**
- **Recognizer:** a feed transaction to POSM 0x58daec3116aae6d93017baaea7749052e8a04fa7, selector ac9650d8, 2,276 bytes, value 0. It is a multicall of initializePool (PoolKey 0x0 / token, fee 100, tick spacing 1, hooks 0, sqrtP 792280926924313289846529216293289), permit 002a3e3a, and modifyLiquidities with MINT_POSITION over [-887272, 184216] and L 100000088127620690885293. Arm the pool from the calldata; also accept the second fingerprint (8.351e32 / 9.487e22).
- **Trigger:** the first transaction to 0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6 with selector e6cb474f, 484 bytes, value 0, that is a buy. A buy has word 1 equal to the sender itself, word 7 = 0x0 (ETH in) and word 8 = the armed token. A sell has word 1 = the router and the token in word 7.
- **Fire block:** fire at the end of the trigger's block so the buy lands at c1+1. Accept +2 or +3 and skip anything later. Price the buy as 0.0058 ETH at minOut = quote x 0.97.
- **Exit:** sell so it lands 50 blocks after our buy. Also record two shadow exits: one at +40, and one that sells early if no router buy follows within 20 blocks.
- **Log:** every pull (POSM dd46508f from the launch wallet) relative to the first router buy and to our phantom buy.

**Dry-run pass criteria**
- The engine's prices are within 0.5% of the chain replay.
- Mean of at least +5% after two fees and gas, median of at least +2%.
- At most 5% of rides have a pull at or before the planned sell.
- No front trades lost to slot occupancy, or that loss is counted against the profit.

**2. Live at $5 (0.00195 ETH), 50 rides.**
This is the trap test, because our real buy will be the first outsider of that size these pools have seen.
- Realised mean of at least +5%.
- At most 2 stakes lost.
- The pull-to-our-buy delay distribution is no shorter than in the dry run: no pull within 60 blocks of our buy above the dry run's rate.
- The operator's buying after our buy is not thinner than in the dry run.

Only then go to $15.


### 0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|true
real_candidate=False confidence=high


**identity**
A third, separate operator ("operator C"). It is neither the volume bot nor operator A, but it runs operator A's playbook: its own scripted crowd, a pull through POSM soon after an outsider buys, and money looped through fresh hop wallets.

It is one serial money chain:
- Deployer N's nonce-8 transaction sends its pull proceeds through two fresh hop wallets (each used once) to deployer N+1. I traced this twice to the wei: 6.19972 to 6.19971 ETH from fresh deployer 0x6ec9cfc5 to 0x8d527d9f, and 8.07886 to 8.07885 ETH from the census's last deployer 0x69d1f429 to 0x6ec9cfc5.
- Deployer 0x8d527d9f then sent 2.0997 ETH straight to crowd router 0x628bd69e, 115 blocks after its funding.

So the scheduled buyer is the operator, funded by the launch wallets: the crowd's ETH goes into the pool and comes back at the pull, and only an outsider's ETH is profit to it.

Crowd details:
- Three routers with identical code (20,733 bytes, hash 0x89495e4b...): 0x410499a0 and 0xebe93d2f (both hold 0 ETH now) and 0x628bd69e (5.22 ETH, the only one used in the 27 fresh launches).
- 480 keeper wallets (261 of them also sell). The tokens go to the keeper itself.
- Census-wide, the routers trade only this family and its hooked sibling.

No overlap with operator A: none of the keepers, deployers or any swap sender in these pools is in research/session_oct9_10/money/loop.json (crowd 32, dispatchers 37, sweeps 37, chains), nor operator A's launcher or its deployer.

Different from the volume bot: no use of its router 0x1cbaf24d (buys or pulls), and a different launch path (PM.initialize from the EOA, then a POSM 1,380-byte mint). Its decoy routers 0x65050a9b and 0xfd1b271f appear here only as small outsiders, and one of their buys (0.000119 ETH at +110) was followed by a pull 4 blocks later.


**recomputed**
I wrote my own replay rather than reusing the analyst's shift model. It re-executes every swap by its own input amount; checked against the chain, the worst sqrtP error is 1.2e-12. I also fetched 6,407 transactions: every swap up to add+600 in all 192 pools, every swap in the 80 blocks before each pull, and each pool's add and pull.

Census (48 h): 192 launches (96 a day), 192 deployers. Initialize is the deployer's nonce 2 (165), 1 (26) or 3 (1). The POSM mint (dd46508f, 1,380 bytes, from the deployer, nonce 6/5) comes 37-213 blocks later, median 41. 77 one-sided mints carry value 0; 115 are full range at 3.0 / 3.5 / 4.0 ETH. The five (sqrtP, L) pairs are confirmed.

Crowd: the first crowd buy is at add +68/72/82/110/231 (min/p10/p50/p90/max). Its size is 0.0425 ETH x45, 0.0312 x43, 0.0082 x21. There are 66 distinct first-6 size sequences, the top one repeated 43 times. The crowd also sells: 444 sells of up to about 0.3 ETH, the first at add +313 to +2689 (median +379) in 130 pools.

Pulls: 57 within 3,000 blocks, all full, all by the deployer through POSM dd46508f (its nonce 7 or 6). 15 fall at +223..+232. The three early ones (+81, +114, +199) each came exactly 4 blocks after an outsider buy (0.00031, 0.000119 and 0.0005 ETH).

Fresh, out of sample: 27 launches between the census head and block 85,326,951 (18:20 to 21:40 UTC). Same shape. Only the crowd router 0x628bd69e is used now. Pools no outsider bought into are pulled at add +4,830..+5,131.

Returns with no reaction to our buy (all $15, after two fees and $0.012 gas):
- Ride +1 to +180: n 192, +7.19% mean, +6.77% median, 97.9% win, 2 pulled, $1.08 a trade. My random 96: +6.04%. Second half: +7.02%. Fresh 27: +8.63%, 0 pulled.
- Follow (crowd1+1, hold 100): +5.99%.
- Front (+1 to crowd1+1): +1.10%.
- Literal front (+1 to +20): -0.18%.
So the analyst's arithmetic is right. The world it assumes is the wrong one.

With the operator's observed reaction to an outsider buy (25 measured delays, below) applied to our buy:
- Ride: -95.8% mean, 96% of stakes lost (-$1,379 a day).
- Follow: -49%.
- Front: -49%.
Counting only the 4-5-block reactions (8 of 25): ride -27%, follow -28%, front -31%. The ride breaks even only if the operator reacts less than 6.7% of the time.

Scripts are in /tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/skeptic_0x8366a39cc670b4001a1121b8f6a443a643e409/: s2_fetch_txs.py, s4_timeline.py, s6*_reaction/exposure, s7_replay.py, s8/s9 identity, s10/s11 fresh, s12* money, s13_sniper.py, s14_reaction_ev.py. Results are in reaction.json, replay.json, fresh_summary.json, reaction_ev.json, money.json and hops.json in the same folder.


**strongest_objection**
This is a trap: the operator pulls the liquidity soon after an outsider buys, and our $15 buy would be the biggest outsider buy this family has ever seen.

Census, all transactions fetched up to add+590:
- 14 pools had a first outsider buy of at least 1e-4 ETH. 5 were pulled exactly 4 blocks after it, and 13 within 144 blocks (delays 4, 4, 4, 4, 4, 15, 78, 102, 103, 104, 106, 113, 144; one never).
- The chance of a pull in any random 6-block window is 0.16%.
- Pools with an outsider buy of at least 1e-4 before +200 were pulled by +240 in 6 of 6. Pools with no outsider buy at all: 1 of 86.
- Later in the window, 0.000205 and 0.00196 ETH buys were also followed by pulls 4 and 5 blocks later.

Fresh 27 launches:
- Every outsider buy of 0.0003 ETH or more (11 of 11, 0.0004 to 0.02 ETH) was followed by a pull 4, 4, 4, 11, 85, 91, 106, 159, 163, 166 or 166 blocks later.
- Untouched pools ran to the scheduled pull near +4,900.

Combined, 24 of 25 outsider buys were followed by a pull within 166 blocks. The ride holds 179 blocks.

The claim's two "pulled" ride trades (+81, +114) and the +199 pull were exactly these reactions.

The analyst's trap test used the sniper 0xe9d83e95. Its 128 buys here are all between 9.01e-5 and 9.99e-5 ETH, never at or above 1e-4, while in other families it buys 0.00019-0.0005 ETH. The sniper is tuned to stay under this operator's trigger, so "no reaction to a 1e-4 buy" is just what that test was bound to show.

No outsider buy above 1e-4 has ever come before the crowd, so add+1 itself is untested, but the evidence points the other way.

The capacity claim is also misdecoded. Calldata word 7 of 7169b574 is the token-side amount: a crowd sell carries its token input there, with word 6 = 0 and word 8 the buy/sell flag. It is not a minOut. This does not matter at $15 (our buy moves the price about 0.3%), but it is not the evidence the analyst said it was.


**live_test**
A dry run cannot settle this. A dry run never buys, so it cannot trigger the reaction pull, and that reaction is the whole question. The paper numbers (+7.2% for the ride) are already reproduced exactly, and the chain already answers the question: 24 of 25 outsider buys were followed by a pull within 166 blocks. My recommendation is not to trade this family and not to spend a dry-run slot on it.

If the owner still wants it closed with real money, a cheap live probe would do it:
- Recognizer: arm on PM.initialize (to 0x8366a39c, 6276cbbe, 196 bytes, currency0 0, fee 500, tick spacing 1, hooks 0) from a sender at nonce 1-3.
- Fire: on the same sender's POSM dd46508f 1,380-byte MINT for that PoolKey, about 41 blocks later. Take L and the range from the MINT; for a one-sided mint, start at the range's upper edge. The buy lands at add+1.
- Size: 0.00015 ETH (about $0.39), above the 1e-4 trigger.
- Exit: sell at add+180. The probe cannot outrun a pull; it only records whether one comes.
- Scale: 20 launches, about $8 at risk.

Pass/fail:
- It fails at 2 or more pulls within 180 blocks of our buy. The chain's evidence predicts about 19 of 20.
- To clear the ride's 6.7% break-even with confidence would take at most 1 pull in about 45 probes.
- Then repeat at the real 0.0058 ETH size before trusting the dollar figures.


### 0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true
real_candidate=False confidence=high


**identity**
The scheduled buyer is the operator. It is not the volume bot, and not operator A's known launcher or crowd, but it runs operator A's money-loop design with its own small pot.

Proof that the crowd is the operator's own money: I scanned full blocks around 3 pools (Sep 29 0x8a1207ee, Oct 3 0x3ac5b6fc, Oct 10 0xcee0878d). Each pool has a fresh dispatcher EOA:
- Its nonce 0 sends the launch wallet 2.01 / 1.61 / 1.5 ETH.
- Its nonces 1-10 send the 10 fresh crowd wallets their exact buy sizes plus gas, 800-1,200 blocks before the launch.
- The launch wallet then deploys the token (nonce 0), makes 1-2 approvals and launches (nonce 3 or 4), and pulls through POSM dd46508f.
- About 85 blocks after the pull, all 10 crowd wallets (nonce 1) send their leftover ETH back to the launch wallet.
- The launch wallet (nonce 5) forwards the whole pot to the next dispatcher.

Example chain on Oct 10: 0xf0aa360f (launch wallet of the previous pool, 0xad44a81c) sends 2.514343 ETH to dispatcher 0x77309bde. That dispatcher funds launch wallet 0x5fe0dc07 and 10 crowd wallets for pool 0xcee0878d. After the pull, 0x5fe0dc07 sends 2.514575 ETH to dispatcher 0x7575c8ea, which funds launch wallet 0x44ce1a5b and the 10 crowd wallets of the next pool, 0xc99153ca (0x7f253e45 and 0x76ad533e are its first crowd buyers). The pot grew from 2.15 ETH (Sep 29) to 2.51 ETH (Oct 10). That growth is the operator's take from outsiders. The crowd never sells.

Not the volume bot:
- Its router 0x1cbaf24d shows up in 0 of 339 pools, for buys or pulls.
- The pulls are POSM dd46508f calls from the launch wallet, not a0f7978d.
- The fees are 100/500, not 2500, 10000 or 100xx.
- The 1,444-byte POSM multicall is just the standard create-and-mint layout.

Not operator A's known pots:
- No 0x3194e326 launcher.
- The crowd is fresh nonce-0 wallets with 1,284-byte UR calldata, not the 32 recurring wallets with 1,124-byte calldata.
- The pot is about 2.5 ETH, against 7.01, 4.86 and 3.5 ETH.

But the design is operator A's: a dispatcher whose nonce 0 funds the deployer and whose nonces 1..N fund the crowd; a pull through POSM dd46508f; a pull or abort on real outside buys. It is most likely the same panel or toolkit with a separate pot.

Shared wallets are not identity evidence:
- 0xe71a69f4 (2e-6 ETH at +3) is a chain-wide dust bot.
- 0x93b07902 and 0x858b1c3e (2.4e-5 ETH at about +1000) and 0x0b410a5f are dust or tiny traders seen in many families.
- Outsiders routing through 0x65050a9b (0x7a95d600, 0xa3a428d9 and others) were rugged here, so that router looks like a public trading-bot router, not the volume bot's decoy.


**recomputed**
The analyst's arithmetic holds on its own sample; the sample is the problem. I rescanned PoolManager Initialize logs from Sep 11 to Oct 10 22:06 UTC (head 85,336,458) and found 339 launches with the same shape: POSM ac9650d8, 1,444-byte calldata, fee 100/ts 1 or 500/ts 10, value of at least 0.4 ETH. For every pool I fetched every swap tx and every pull. 316 pools had a crowd (UR 3593564c, 1,284 bytes, nonce 0); 23 had none.

Count:
- Census window: 17 fee-100 pools plus 5 fee-500, matching the claim.
- After the census (Oct 10 18:20-22:06): 7 more.
- Over the month: about 11 a day on average, but in sessions. Some days have none (Sep 18-20, 23, 25-26, 30, Oct 4, Oct 8); Oct 6 had 48.

Schedule, claim17 vs the month:
- First crowd buy (min/p10/p50/p90/max): 258/277/319/577/921 vs 160/223/306/577/1772.
- 10th crowd buy: 1304/1590/1729/2360/2367 vs 813/1381/1729/2460/4633.
- Crowd buys per pool are not always 10. Month: 10 in 241 pools, 8 in 23 (mid-Sep era), 11 to 19 in 6, 1 to 9 in 69.
- minOut/fill is 0.98 from Sep 11-27 and 0.80 from Sep 28 on, and the quote is fresh at send time. So minOut never binds on a buy 250+ blocks earlier. The capacity claim holds.

Pull margin (pull minus 10th crowd buy):
- claim17 min/p10/p50: 58/93/564.
- Month: 47/89/591.
- Pools where a 0.005 ETH outsider held: 52-190, median 73. The operator pulls soon after the crowd ends when outside money is in the pool.

Front, family rule (buy at +1; sell the block after the 10th crowd buy; sell at +640 if no crowd buy by then; deadline +2400), exact constant-L replay:
- claim17: +60.85% mean, 54.49% median, 94% win, 0 pulled first. This reproduces the claim exactly.
- After the census (7): +106% mean, 0 pulled.
- All 339: +49.9% mean, 77.9% win, 49 pulled first (14%).
- Since Oct 5 (121): +32.6% mean, 21 pulled first.
- The 29 pools where an outsider of our size (0.002 ETH or more) held before the crowd: -30.1% mean, median -100%, 15 pulled first.

Follow (buy after the first crowd buy, sell after the 10th):
- Month, 316 crowd pools: +47.9%, 32 pulled first, no reaction modelled.
- When an outsider of 0.002 ETH or more bought mid-crowd, the crowd still reached 10 in only 2 of 17 cases (1 of 5 at 0.002-0.01 ETH, 1 of 12 above).

Selling into the first crowd buy: +1.3% for the month, -0.9% since Sep 28.

Scripts and data are in /tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/skeptic_0x58daec3116aae6d93017baaea7749052e8a04f/f1444_100/ (b2-b9, c1-c9, d1-d4; results in data/c3.json, c6_trap_*.json, c7_trap_mid*.json, c8.json, c9.json).


**strongest_objection**
The trade needs us to be the thing this operator reacts to: an outside holder of real size before and during its crowd. The 17-pool window happens to contain almost no such holders, and the month shows the reaction.

Trap test: an outside wallet buys before the first crowd buy and is still holding 60 blocks later. Share of pools where the crowd still reached 10 before the pull:

| Early holder size (ETH) | Pools | Crowd reached 10 | Aborted (pulled with no crowd buy) | Crowd cut |
|---|---|---|---|---|
| 0.0001-0.0005 | 93 | 78% | 4 | 14 |
| 0.0005-0.002 | 14 | 6 | 4 | 4 |
| 0.002-0.01 | 25 | 10 | 12 | 3 |
| 0.01 and up | 4 | 1 | 3 | 0 |

With no early holder (Sep 28 on, n=144), the crowd reached 10 in 91% of pools.

Aborts are pulled 77-275 blocks after the early buy, at +173..+341 from launch. That is before the typical first crowd buy, so neither the +640 abort nor a sell at the first crowd buy can save the stake.

The claim calls the reaction to a 0.0058 ETH early buy untested (n=1). It was tested on Oct 5 22:00 - Oct 6 01:41 UTC by wallet 0x578e7a8e..., which bought exactly 0.005 ETH at +61..+136 in 24 consecutive pools, the shape of our trade:
- First 10 pools: crowd completed in 8.
- Last 14 pools: 10 aborts (no crowd, pulled at +182..+966), 2 cuts (3 and 4 crowd buys), 2 completed.
- The operator relaunched every 2-2.5 minutes and kept aborting until the wallet stopped. The next 3 launches without it were normal.
- The most recent case, Oct 10 pool 0x7215ffa6: 0.005148 ETH bought at +586, pulled at +663, no crowd.

So the operator tolerates holders at about 0.0003 ETH (0x5e6ec144 already runs exactly this hold at that size, about $0.40 a trade). It aborts real-size early holders, and it learned to do so within about 10 pools. At $15 the expected value is negative.


**live_test**
A paper dry-run cannot settle this, because the open question is the operator's reaction to a real holder. Paper trading would only reproduce the no-reaction replay (+50-60%). Settling it needs a gated live probe with an explicit loss budget, and only if the owner wants to spend one.

Recognizer (can arm 800-1,200 blocks before the launch):
- In the feed, a fresh EOA at nonce 0 sends 1.0-2.5 ETH (x.x1 ETH, e.g. 2.01 or 1.61) to a fresh EOA.
- Within about 40 blocks, its nonces 1-10 send 0.007-0.2 ETH each to 10 fresh EOAs. Record them as the crowd list, with their amounts (the crowd's total pump is known in advance).
- Arm on the funded EOA's launch tx: to POSM ac9650d8, 1,444 bytes, value equal to the funded amount minus about 0.01, nonce 3-4. Decoded PoolKey: currency0 0, fee 100/ts 1 or 500/ts 10, hooks 0, MINT_POSITION -887272..887272 (or -887270..887270).

Fire: at launch +1.

Exit:
- Sell in the block after the last listed crowd wallet buys. Its tx is UR 3593564c, 1,284 bytes, nonce 0, so the 10th buy is known exactly and there is no counting guess.
- Sell at once if a listed wallet has not bought within 300 blocks of the previous one.
- Hard deadline +2400.
- No exit beats an abort pull; that is what the probe measures.

Gated escalation (a separate position slot, front's slot untouched):
1. 0.0005 ETH on 10 launches.
2. Then 0.002 ETH on 10 launches.
3. Then 0.0058 ETH on 30 consecutive launches across at least 2 sessions. The 0x578e7a8e wallet was tolerated for about 10 pools before the operator switched to aborting, so a short pass means nothing.

Pass at each step:
- At least 90% of probed launches get all 10 listed crowd buys before the pull.
- No pull before the first crowd buy.
- The pull lands at least 50 blocks after our sell.
- Unprobed launches in the same session stay at about 91% complete, as a control.

Fail and stop at the first of:
- 2 aborts or cuts in any step.
- Any pull within 300 blocks of our buy.

Loss budget: about $15 × 3 = $45 at the final step before the stop triggers.

Expected result from the month's record: fail at the 0.002 or 0.0058 step (60% abort or cut at our size class).
