#!/usr/bin/env python3
"""Compose results.json (the orchestrator's per-family rows) from results_raw.json, calib.json, validate.json, router27/r27_cap/r27_logs."""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "results_raw.json")))
C = json.load(open(os.path.join(HERE, "calib.json")))
K1 = "0xfcd182416ca91a9e88e9fe44e4f78ea3cb2c15c7|6fe958d8|68|100000|200|false"
K2 = "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|838974|9303|true"
K3 = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|3000|60|true"
K4 = "0x815542e8b392389a1389e22e588e4b62a67ade72|7c33638d|769|30000|200|true"
fam = []
fam.append({
 "key": K1, "known": "none", "count": 22, "launches_per_day": 11.0,
 "launcher": "one wallet 0x26e8134ecc3af5cce32f34b03e7bd2f318b25158 (nonce 59.4k-61.7k, about 1,100 txs a day) calls the hook contract 0xfcd182416ca91a9e88e9fe44e4f78ea3cb2c15c7 (21,824 bytes; it is also the pools' hook) with 6fe958d8(wallet, token), 68 bytes, value 0; fee 100000 (10%), tick spacing 200. All 22 launches Oct 9 03:15-17:10 UTC (21 of them 03:00-09:00), none since. The same contract runs the 0.3%/1%/3% tiers and USDG pools: 483 pools with its hook in the window",
 "first_buy": "none: 0 buys and 0 sells of any size in 22 of 22 pools within 3,000 blocks. The launch range sits 25-1,976 ticks ABOVE the initial price (ETH-only, 0.0001-0.027 ETH of liquidity), so a buy cannot get any token. The only Swap events (6 pools) are zero-amount swaps by the deployer itself through its contract 0xd809ec17 (6b4cc5f1) after the liquidity is removed (3,185 such zero swaps in 483 pools chain-wide, 0 buys)",
 "pull": "the census 'pull' at +11..14 (15 pools) is a remove-and-re-add of the same position in one tx (net 0), not a pull. Real removals: 6 of 22 (27%) within 3,000 blocks, at launch +1745/+2837/+2912 (p10/50/90), all by the launch wallet through 0xfcd18241 (4596ca11); offsets from a first buy: n/a (no buys)",
 "outsiders": "none (no buys at all); trap test not applicable",
 "front_rule": "n 0: no buy-side liquidity in 22 of 22 (the range is above the price); $0 a trade, $0 a day",
 "follow_rule": "n 0 (no buy >= 0.0002 ETH); $0",
 "capacity": "n/a (no scheduled buy)",
 "engine_config": "",
 "verdict": "no-schedule", "candidate_score": 0,
 "notes": "Not a launch-and-buy operator: liquidity management by one wallet (ETH-only range above the price, re-minted at +11..14, removed at about +2,800, then zero-amount price moves). Nothing to front or follow."})
fam.append({
 "key": K2, "known": "none", "count": 20, "launches_per_day": 10.0,
 "launcher": "one wallet 0xe8d7c2a9c81d89e5282b6dc63346fb014532cc3c (nonce 37.2k-37.5k) calls PoolManager.initialize directly (6276cbbe, 196 bytes, value 0) with fee 838974 (an 83.9% LP fee) and tick spacing 9303, hooks 0; the liquidity comes 15/20/30 blocks later (min/median/max) in a separate POSM tx: full range +-883785, exactly 0.0004 ETH of depth in all 20 pools. Launches spread Oct 8 18:25 - Oct 10 08:55 UTC",
 "first_buy": "1 of 20 pools (5%): +321 blocks, 0.000207 ETH, through the aggregator 0x9e90b6b4 (81040127) from 0xf681f76c (nonce 12,263); the only other swaps are a 0.00022 ETH buy at +473 via 0x6131b5fa (e21fd0e9) and one sell via 0x901772fd: aggregator flow routed into an 84%-fee pool. Offset p10/50/90 321/321/321, size 0.000207; one sender; no schedule",
 "pull": "0 of 20 pulled within 3,000 blocks",
 "outsiders": "none before any buy (no schedule); trap test not applicable",
 "front_rule": "as specified (buy at launch+1): n 0, the liquidity is not live until +15..30 (exit no_liquidity_at_buy). Counted from the liquidity block +1 instead: n 20, mean -93.4%, median -93.8%, win 0%, pulled-first 0, -$14.01 a trade, -$140 a day (two 83.9% fees)",
 "follow_rule": "n 1 (the +321 buy): -94.0%, win 0%, pulled-first 0, -$14.10 a trade, -$7.05 a day",
 "capacity": "minOut assumed 0.99 x the launch-state quote (aggregator calldata not decoded): 0.00001 ETH of room; irrelevant",
 "engine_config": "",
 "verdict": "no-schedule", "candidate_score": 0,
 "notes": "A fee honeypot for aggregators (0.0004 ETH of liquidity behind an 83.9% LP fee), not a launch/buy/pull operator. Any buy loses 84%."})
fam.append({
 "key": K3, "known": "none (known_by_rule vbot-other: the standard create-and-mint layout, no sign of the bot)", "count": 18, "launches_per_day": 9.0,
 "launcher": "15 different wallets (0xc28b7a41 x4 with value 1e-6; the rest one each, nonces 3-2,322) using the standard Uniswap create-and-mint multicall (initializePool + MINT_POSITION/SETTLE_PAIR/SWEEP); values 0 x10, 1e-6 x4, 0.0005 x2, 1e-5, 0.0504; single-sided token ranges in 10, full range in 8. 18 launches Oct 8 18:48 - Oct 9 22:23 UTC, none since. Not one operator",
 "first_buy": "any size: 18 of 18, offset p10/50/90 1/3/3 blocks, size 2e-6/2e-6/0.001 ETH; 15 of 18 are the chain-wide dust bot 0xe71a69f4 (2e-6 ETH via the UR at +3). First real buy (>= 0.0002): 6 of 18 (33%), offset p10/50/90 0/1/182, size 0.00021/0.001/0.004 ETH, 5 senders through 5 different routers: 3 are 0.001 ETH snipes at +0/+1 in deployer 0xc28b7a41's pools (contracts 0x1e7634e5 / 0xfe1323d6, wallets 0x11f4fc80 / 0xa495ca86), the rest unrelated. No schedule",
 "pull": "0 of 18 pulled within 3,000 blocks",
 "outsiders": "only the dust bot (15 pools, 2e-6 ETH) before the first real buy; trap test not applicable (nothing is pulled)",
 "front_rule": "n 18, mean -0.43%, median -0.65%, win 5.6% (1 of 18), pulled-first 0, -$0.064 a trade, -$0.57 a day (17 of 18 sold at the +20 deadline into nothing; 3 first real buys came at or before our +1)",
 "follow_rule": "n 6, mean -0.56%, median -0.52%, win 0%, pulled-first 0, -$0.083 a trade, -$0.25 a day",
 "capacity": "minOut assumed 0.99 x the launch-state quote (UR / sniper calldata not decoded): room p10/50/90 0.00001/0.00003/0.00025 ETH; 5 of 6 first real buys have less room than our stake",
 "engine_config": "",
 "verdict": "no-schedule", "candidate_score": 0,
 "notes": "Sub-cluster worth knowing, too small and stopped: 3 pools launched by fresh wallets (nonce 3; value 0.0005/0.0005/1e-5 ETH, full range, 0.0005/0.0005/0.00001 ETH of depth) get a burst of 13-14 buys of 0.0001 ETH (4e-6 in the third) from 13-14 fresh wallets (nonce 0/1) through router 0x27fad47c (0f4f745a, 932 bytes) at +65..68 / +100..102 / +135..138, then the deployer's own tiny UR buy and sell; never pulled. Its calldata decodes: word 6 = amountIn, word 7 = minOut = 1e-4 x the launch quote, so 0.055 ETH can sit ahead. Front at $15 (buy +1, sell one block after the burst): +23.5% ($3.53) in the two 0.0005 pools, -0.3% in the 1e-5 pool (7 of its buys would revert); the profit is capped by the burst (0.0014 ETH). Chain-wide the router made 74 swaps in 13 pools (10 initialized before the window), the last at block 84,156,140 (Oct 9 about 19:00 UTC): stopped. At most about $3.5 a day while it ran. Files router27.json, r27_cap.json, r27_logs.json."})
fam.append({
 "key": K4, "known": "none", "count": 18, "launches_per_day": 9.0,
 "launcher": "launchpad contract 0x815542e8b392389a1389e22e588e4b62a67ade72 (13,681 bytes), 7c33638d, 769 bytes, value 0: creates the token and mints a single-sided token range [-887200, tick0] through the POSM in one tx (two price levels, tick0 184000-184200 / 193200-193400); 9 wallets (0x532c5a3d x7, 0x461eb1fc x3, 0xe950da78 x2, six others once; nonces 0-280). 18 launches Oct 8 18:39 - Oct 10 12:53 UTC",
 "first_buy": "any size: 2 of 18 (11%): +57 blocks 0.019 ETH via the UR from a nonce-1 wallet 0x8ae74bb7, and +1544 2.4e-5 ETH via Multicall3 from 0x18dd3c14 (nonce 821k). First real buy 1 of 18. No schedule",
 "pull": "0 of 18 pulled within 3,000 blocks",
 "outsiders": "none; trap test not applicable",
 "front_rule": "n 18, mean -5.99%, median -5.98%, win 0%, pulled-first 0, -$0.90 a trade, -$8.09 a day (two 3% fees, nothing to sell into)",
 "follow_rule": "n 1: -5.98%, win 0%, pulled-first 0, -$0.90 a trade, -$0.45 a day",
 "capacity": "1 buy through the UR (nested execute: minOut not decoded), assumed 0.99 x the launch-state quote: 0.0212 ETH",
 "engine_config": "",
 "verdict": "no-schedule", "candidate_score": 0,
 "notes": "A token launchpad whose pools nobody trades in the window; no scheduled buy, no pull."})
v = R["vbot-v2.433"]; a = R["operator-A"]
fam.append({
 "key": "vbot-v2.433: 0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true at value 2.4333285 ETH", "known": "vbot-v2.433 (control)", "count": 1843,
 "launches_per_day": 921.8,
 "launcher": "a fresh wallet per launch (1,843 senders for 1,843 launches), POSM multicall, exactly 2.4333285 ETH. Rate: 68-102 per 6 h from Oct 8 18h to Oct 10 06h (270-410 a day), then 530 (Oct 10 06-12h) and 758 (12-18h) per 6 h: about 3,000 a day on Oct 10 afternoon",
 "first_buy": "first non-launch buy of any size: offset p10/50/90 2/3/3, 2e-6/2e-6/0.00495 ETH = the dust bot 0xe71a69f4 (940 pools) or the bot's decoy router 0x65050a9b (854). The scheduled buy (bot router 0x1cbaf24d, c1120e3d, 324 bytes): 1,842 of 1,843, offset p10/50/90 8/9/10 (min 6, max 130), size 0.0495/0.175/0.25 ETH, 31 sender wallets (top 71/68/67 pools)",
 "pull": "80.4% within 3,000 blocks; from launch p10/50/90 11/13/127; from the bot's buy 3/3/117 (3 in 1,044, 4 in 101, 2 in 14), never before it; by the launch wallet through the bot's router (a0f7978d) in 1,482 of 1,482 known",
 "outsiders": "no real-size outsider other than our relay (5 pools with 2e-5..5e-5 ETH). Decoys ahead of the bot in 1,128 pools; since Oct 10 14:00 UTC they buy 0.00495-0.0099 ETH ahead (457 pools), leaving less room than our 0.0058 in 229 (the bot's buy would then revert; the front trade earns about 0). Trap test with our relay as the outsider: 1,047 pools with our 0.0058 ahead: pulled 99.8%, at bot+3/3/3, 0 before the bot; 795 without: 54.8% pulled, bot+3/78/1053. Same UTC hours: 876 of 880 relay pools vs 79 of 112 others pulled within 4 blocks of the bot. The pull comes sooner after an outsider, but always after the bot's buy and 2 blocks after a sell at bot+1: not a trap for front",
 "front_rule": "n 1843, mean +11.86%, median +14.01%, win 94.6%, pulled-first 0, $1.78 a trade, $1,640 a day at 921.8 a day. Calibration: the live-audit window Oct 10 09:07-11:40 prices n 409, mean +13.98%, median +16.17% (live: +13.97% / +16.25%). By bot size: <0.03 ETH +0.9%, 0.15-0.22 +13.1%, >0.22 +18.1%. Oct 10 12-18h slice +9.4% (decoy-filled pools)",
 "follow_rule": "n 1842, mean -35.4%, median -0.57%, win 0.2%, pulled-first 646, -$5.32 a trade (the pull at bot+3 beats a sell at bot+5): wrong rule for this operator, as expected",
 "capacity": "minOut decoded (word 4) in 1,842 of 1,842: minOut / launch-state quote 0.99 (min 0.9898). Total room from the launch state p10/50/90 0.01241/0.01271/0.01289 ETH (handoff: 0.0122-0.0124); room left after the others' buys ahead 0.00528/0.01253/0.01283, under 0.0058 in 229 pools",
 "engine_config": "already live as front (HANDOFF 3.2)",
 "verdict": "control-known", "candidate_score": 0,
 "notes": "Pricer check: replaying our relay's real round trips at their real blocks and sizes reproduces the chain's realized return to 9e-16 in all 667 trades where our buy was last in its block and our sell first in its block (1,045 trades in all, median |error| 4e-16; the rest differ only by intra-block order, max 0.8%)."})
fam.append({
 "key": "operator-A: known == operator-A (launcher 0x3194e32622c5d860a0572c74edda99dcfd8fc827, 2fcb9108; 67 strict families)", "known": "operator-A (control)", "count": 77,
 "launches_per_day": 38.5,
 "launcher": "fresh wallet per launch (77 senders) through the launcher 0x3194e326, values 1.88-2.7 ETH, the fee varies per launch",
 "first_buy": "any size: the dust bot 2e-6 ETH at +3 (74 of 77). First real buy = the crowd (UR execute, 1,124 bytes) in 75 of 77: offset p10/50/90 24/54/66 (min 17, max 1193), size 0.0143/0.0547/0.1203 ETH, 10 wallets (top 25/23/15 pools)",
 "pull": "85.7% within 3,000 blocks; from launch p10/50/90 51/224/2180; from the first crowd buy 6/165/2157; by the launch wallet through the POSM (dd46508f) in 66 of 66 known",
 "outsiders": "no real-size outsider before the crowd in the window (27 pools with 6e-6..6e-5 ETH, decoys in 3, dust in 77); the census has no case to test (the handoff's Oct 8: pull 5-13 blocks after each of our buys)",
 "front_rule": "n 77, mean -0.51%, median -0.54%, win 1.3%, pulled-first 0, -$0.077 a trade, -$2.95 a day (the crowd comes after +20)",
 "follow_rule": "n 75, mean +4.33%, median +3.27%, win 84%, pulled-first 0, $0.65 a trade, $24.4 a day at 37.5 a day (live record +2-4% at $3; our 31 clean relay round trips reproduce exactly)",
 "capacity": "UR execute is nested: minOut not decoded; assumed 0.99 x the launch-state quote: room p10/50/90 0.00823/0.01148/0.01729 ETH",
 "engine_config": "already live as follow (HANDOFF 3.1)",
 "verdict": "control-known", "candidate_score": 0,
 "notes": "Controls calibrate the method: v2.433 front reproduces the live result, operator A follow reproduces the live sign and size."})
out = {"method": "analyse_4/ana.py + analyse.py: census replay (relay swaps removed, every swap replayed by its own shift, our buy at the end of B, our sell at the head of S, minOut drop for the bot's c1120e3d buys, net-negative-liquidity tx = pull, gas 2 x 104,000 x launch-block base fee, $15 = 0.0058 ETH)",
       "families": fam, "raw": R, "calib_v2433": C}
json.dump(out, open(os.path.join(HERE, "results.json"), "w"), indent=1, default=str)
print("wrote results.json", len(fam))
