"""the structured output (families_out.json) from results.json / calib.json / opc_timeline.json / sel7fde.json: the numbers are read, the prose wraps them"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "results.json"))); C = json.load(open(os.path.join(HERE, "calib.json")))
def rs(s, extra=""):
    if not s or not s.get("n"): return "n 0" + extra
    return (f"n {s['n']}, mean {100*s['mean']:+.2f}%, median {100*s['median']:+.2f}%, win {100*s['win']:.0f}%, pulled-first {s['pulled_first']}, "
            f"${s['usd_trade']:+.3f} a trade, ${s['usd_day']:+.2f} a day ({s['trades_day']}/day in the 48 h window)" + extra)
c100, c500, call, ch = R["opC-fee100"], R["opC-fee500"], R["opC-window-all"], R["opC-with-hist"]
out = []
out.append({
 "key": "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true", "known": "none (new: 'operator C', a ten-wallet slow crowd)", "count": 17,
 "launches_per_day": 8.5,
 "launcher": "POSM multicall ac9650d8, 1,444 bytes (initializePool + MINT_POSITION full range -887272..887272 + SETTLE_PAIR + SWEEP), value 2.0 ETH x13 / 1.8 x3 / 1.5 x1 (exact wei 1999999999999992334, 1799999999999992727, 1499999999999993361, also ...7576/...7700 at tick 200311/201364), liquidity sqrt(value x 1e28 tokens) e.g. L 141421356237309504880168 at tick 223338; a fresh launch wallet per pool (17 wallets for 17 pools, launch nonce 3 in 15, 4 in 2). Same operator also launches the fee-500 ts-10 sibling (5 pools) and did 13 more on Oct 7 (pre-window, fetched: 11 fee 100 + 2 fee 500). Sessions: Oct 7 (13 in ~4.4 h), Oct 9 12-24h UTC (9), Oct 10 12-18h UTC (13).",
 "first_buy": "first non-launch buy = the chain-wide dust bot 0xe71a69f4 (2e-6 ETH via UR) at +3 in 17/17. First real (>=0.0002) = outsider 0x5e6ec144 (0.0003 ETH at +85..+98) in 13, the crowd in 4. The SCHEDULED buy = the operator's crowd: Universal Router execute 3593564c, 1,284-byte calldata, sender a brand-new wallet (nonce 0), 16 distinct wallets for 16 pools; first crowd buy at +258/+277/+319/+577/+921 (min/p10/p50/p90/max), size 0.0185/0.0534/0.0971 ETH (p10/50/90, min 0.0072); present in 16/17 (94%). Then exactly 10 crowd buys per pool in 16/16 (33/33 incl. sibling and Oct 7), gaps p10/50/90 96/139/208 blocks, the 10th at +1304..+2367 (p50 1729), totalling 0.4834-0.4894 ETH on 2-ETH pools (0.678-0.683 on 1.8, 0.974 on 1.5): a fixed pump of the price by about +54% (2 ETH) / +90% (1.8) / +170% (1.5). The crowd never sells.",
 "pull": f"10/17 (58.8%) pulled within 3000 blocks; from launch p10/50/90 1567/2019/2791 (min 663, the crowd-less pool); from the first crowd buy p10/50/90 1450/1746/2472 (min 1309); from the 10th crowd buy min 58, p10 93, p50 291, p90 715 blocks. All by the launch wallet through POSM modifyLiquidities dd46508f, full liquidity. Window union (22): {call['pull']['frac_3000']} within 3000; after the 10th crowd buy min 58 / p10 93 / p50 431.",
 "outsiders": "Before the first crowd buy: real-size (>=0.0002 ETH) outsiders in 13/17 pools (all Oct 10; 0/5 fee-500 Oct 9, 0/13 Oct 7): 0x5e6ec144 0.0003 ETH at ~+90 in 13 (holds through the crowd, sells at +1766..+1999 for about +40-50%: the hold rule at 1/20 our size), 0x13301ff0 0.0003-0.0005 at +91..+138 in 8 (sells right after the first crowd buy), 0x3155c72d 4e-5, 0xc74d9ced 0.005148 in 1; 0x0b410a5f buys 7e-5 ETH ~13 blocks after the first crowd buy and sells ~80 later in 18 of 22. TRAP TEST: with outsiders (13): crowd came 12/13, pulled<=3000 8/13, pull from launch p10/50/90 1567/2477/2791, pull after the first outsider 1479/2379/2706 blocks; without (22 = 4 fee-100 + 5 fee-500 + 13 Oct 7): crowd came 21/22, pull from launch 1956/2431/2819: no sooner pull after outsiders of <=0.0005 ETH, and a 0.001576 ETH outsider mid-crowd (pool 0x0788f75c) did not stop the crowd. Caveat, n=1: the only outsider of our size before a crowd (0.005148 ETH at +586, in a pool whose crowd had not started) was followed by the pull 77 blocks later (+663) and no crowd; the other crowd-less pool (Oct 7, no outsider at all) was not pulled within 3000 blocks. So 2/35 pools get no crowd regardless; whether a 0.0058 buy before the crowd starts makes the operator abort is untested.",
 "front_rule": "literal (land +1, sell one block after the first crowd buy, or at +20 if none by then; none comes by +20): " + rs(c100["front"]) +
   ". Waiting for the first crowd buy (deadline +600): " + rs(c100["front_wait"]) +
   ". FAMILY RULE (land +1, sell one block after the 10th crowd buy; no crowd buy by +640: sell at +640; deadline +2400): " + rs(c100["front_c10"]["0.0058"]) +
   f" (median hold ~1,730 blocks = 3 min; two pools hit the +640 abort: the crowd-less one sold at +0.45%, 23 blocks before its pull at +663, and the one whose crowd started late at +921 sold at -0.05%, the only loser). Stake sweep, same rule: 0.02 ETH +{100*c100['front_c10']['0.02']['mean']:.1f}%, 0.05 ETH +{100*c100['front_c10']['0.05']['mean']:.1f}%, 0.1 ETH +{100*c100['front_c10']['0.1']['mean']:.1f}% (${c100['front_c10']['0.1']['usd_trade_at_stake']:.0f} a trade).",
 "follow_rule": "literal (buy one block after the first buy >=0.0002 = 0x5e6ec144's 0.0003 at ~+90 in 13 pools / the first crowd buy in 4; sell one block after the next real buy or at buy+4; the next buy is always >4 blocks away): " + rs(c100["follow"]) +
   ". Follow-entry with the family exit (buy one block after the FIRST CROWD buy, sell one block after the 10th): " + rs(c100["follow_c10"]) + " (never enters a crowd-less pool).",
 "capacity": "minOut DECODED from the crowd's UR calldata (V4_SWAP SWAP_EXACT_IN: the word after amountIn = tx value is amountOutMinimum; word 22 of the 1,284-byte layout): minOut = 0.800 x its own fill in 16/16 (a fresh quote at send time with 20% slippage; minOut / launch-state quote 0.7994-0.8000). Real slack: 0.218/0.239/0.241 ETH (p10/50/90, min 0.179) can sit ahead of the first crowd buy before it reverts; under the schema's 1%-of-launch-quote assumption it would be 0.0093/0.0102/0.0103 ETH, but the quote is fresh, so our buy 250+ blocks earlier is inside it. No crowd buy is dropped in any replay up to a 0.1 ETH stake.",
 "engine_config": "recognizer: tx to POSM 0x58daec3116aae6d93017baaea7749052e8a04fa7, selector ac9650d8, calldata 1,444 bytes (the decode_launch layout), value 1.5-2.0 ETH (not 2.4333285), decoded PoolKey currency0 0, fee 100 ts 1 or fee 500 ts 10, hooks 0, MINT_POSITION -887272..887272; launch wallet nonce 3-4. Eligibility: L0 = sqrt(value x 1e28 or 1e27). Fire: any block from launch to ~+180 (nobody but the dust bot and tiny outsiders buys before +188; landing at +1 prices the same). Exit trigger: count crowd buys in the feed: tx to Universal Router 0x8876789976decbfcbbbe364623c63652db8c0904, execute 3593564c, 1,284-byte calldata, sender nonce 0, value 0.007-0.19 ETH, path through this pool's token; sell in the block after the 10th; abort (sell) at +640 if no crowd buy yet; hard deadline +2400; also sell at once on any modifyLiquidities (dd46508f) from the launch wallet. Hold 1,200-2,400 blocks (2-4 min): needs its own position slot (front's one slot would be blocked). Safer entry variant: buy one block after the first crowd buy (same exit).",
 "verdict": "candidate",
 "candidate_score": c100["front_c10"]["0.0058"]["usd_day"],
 "notes": f"candidate_score = the family rule (front, exit after the 10th crowd buy) at $15 on this strict family's 17 launches = ${c100['front_c10']['0.0058']['usd_day']}/day; the literal front/follow rules are flat because the schedule runs at +258..+2367, not +7..+10. The operator as a whole in the window (fee 100 + fee 500, 22 launches, 11/day): " + rs(call["front_c10"]["0.0058"]) +
   f"; with the 13 Oct 7 pools (35): mean {100*ch['front_c10']['0.0058']['mean']:+.1f}%, median {100*ch['front_c10']['0.0058']['median']:+.1f}%, 32/35 up, 0 pulled-first; each session separately +56% (Oct 7), +61% (Oct 9-10 fee 100), +61% (fee 500). Pricer calibration: v2.433 front in the live window Oct 10 09:08-11:40 replays +13.98% mean on 409 pools (live record +14.1%); operator A follow +4.3% (handoff +2-4%). Risks: (1) 2/35 pools get no crowd (one pulled at +663 after a 0.005 ETH outside buy: the abort at +640 exits both); (2) the reaction to a buy of our size before the crowd is untested (n=1, above); (3) small competitors already run this (0x5e6ec144 hold, 0x13301ff0 front, 0x0b410a5f follow) and the operator tolerates them; (4) launches come in irregular sessions (3 sessions in 4 days), so $/day is session-dependent. Price/volume per pool is small (0.48 ETH crowd per 2-ETH pool), but the trade is not capacity-bound below ~0.1 ETH. Scripts and data: analyse_5/analyse.py, pricer.py, opc_timeline.py (every swap's tx: opc_txs.json), fetch_hist*.py + hist_build.py (Oct 7 pools), results.json, calib.json."})
out.append({
 "key": "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|500|10|true", "known": "none (sibling of the fee-100 family: same operator C, not in my assignment list; added for completeness)", "count": 5, "launches_per_day": 2.5,
 "launcher": "same as the fee-100 family (POSM 1,444-byte multicall, 2.0 ETH x4 / 1.8 x1, fresh wallet nonce 3 each), fee 500 ts 10, all 5 on Oct 9 12-18h UTC",
 "first_buy": "dust bot at +3/+4 in 5/5; crowd (UR 1,284 bytes, nonce-0 wallets, 5 distinct) first at +188/+277/+371, 0.016/0.030/0.059 ETH; exactly 10 crowd buys in 5/5, total 0.4837-0.4841 ETH (2.0) / 0.678 (1.8)",
 "pull": "4/5 pulled within 3000; from launch 2025/2631/2798; from the first crowd buy 1748/2396/2504; from the 10th crowd buy 425/1047/1108; launch wallet via POSM dd46508f",
 "outsiders": "no real-size outsider before the crowd in any pool (only the dust bot and 2e-5..6e-5 ETH specks); nothing to test",
 "front_rule": "literal: " + rs(c500["front"]) + ". Wait-600: " + rs(c500["front_wait"]) + ". Family rule (exit after the 10th crowd buy): " + rs(c500["front_c10"]["0.0058"]),
 "follow_rule": "literal: " + rs(c500["follow"]) + ". Follow-entry, family exit: " + rs(c500["follow_c10"]),
 "capacity": "decoded crowd minOut = 0.8 x fill (fresh quote); slack ahead of the first crowd buy 0.214/0.238/0.240 ETH",
 "engine_config": "as the fee-100 family (one recognizer covers both fee tiers)",
 "verdict": "candidate", "candidate_score": c500["front_c10"]["0.0058"]["usd_day"],
 "notes": "count it with the fee-100 family as one operator (window total $" + str(call["front_c10"]["0.0058"]["usd_day"]) + "/day at $15); do not add both scores AND the union."})
for name, key in (("06cb-9f81", "0x9f81695f2d705e81f8fb7a4f8831afe92c4e6b35|7fde822e|804|10000|200|true"), ("06cb-b775", "0xb7758ae7102037e3db22fe472689e6598a78f639|7fde822e|804|10000|200|true"),
                  ("06cb-f6b5", "0xf6b59a71e1a3169bd418169ee20e37e6a7152b5c|7fde822e|804|10000|200|true")):
    r = R[name]
    fr = r["first_real"]
    out.append({
     "key": key, "known": "none", "count": r["count"], "launches_per_day": r["launches_per_day"],
     "launcher": "one EOA 0x06cb3a6841c92525e7a1998328e7c9d37e98d937 (nonce ~2,090-2,300: thousands of launches) calling its own launch contract (" + key[:42] + ", ~19 KB; the wallet moves to a new contract every ~16 launches: 25 contracts with selector 7fde822e in 48 h, calldata 740-932 bytes), selector 7fde822e, 804 bytes, value 0; clockwork: one launch every ~2,922 blocks (5 min) -> 454 launches in 48 h by this wallet (227/day). Pool: fee 1%, ts 200, no hooks, token-only single-sided range [132800, 201800] with tick0 201800 (L 32156000099526845215062): no ETH in the pool at launch.",
     "first_buy": "first non-launch buy: the dust bot 0xe71a69f4 (2e-6 ETH via UR) at +3/+3/+4 in 16/16; first real buy (>=0.0002 ETH) in " + str(fr["n"]) + "/16" + (f" (0.010745 ETH at +843 via the ERC-4337 EntryPoint from 0x0312f701, sold back 3 blocks later by another bot)" if fr["n"] else "") + "; no scheduled buy of any kind. Across the deployer's 454 pools only 5 ever got a buy >=0.0002 ETH (0.029 ETH in all)",
     "pull": "0/16 pulled within 3000 blocks (0 of the deployer's 454)",
     "outsiders": "none of real size (" + ("1 pool: 2e-5/5e-5 ETH specks from 0xfeda1c58 via router 0xf0b7eaaf" if name == "06cb-b775" else "dust only") + "); trap test not applicable (no pull, no schedule)",
     "front_rule": rs(r["front"]) + " (no scheduled buy: every trade sold at +20 into nothing, losing two 1% fees and gas)",
     "follow_rule": rs(r["follow"]),
     "capacity": "no scheduled buy, nothing to decode; n/a",
     "engine_config": "none: nothing to trade",
     "verdict": "no-schedule", "candidate_score": 0,
     "notes": "A pool-spam launcher (single-sided token liquidity, no ETH, nobody buys, never pulled); the whole 7fde822e loose family (490 pools, 5 deployers) looks the same (sel7fde.json). Not an operator with buys to front-run."})
v, a = R["control-v2433"], R["control-opA"]
out.append({
 "key": "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true", "known": "vbot-v2.433 (control)", "count": v["count"], "launches_per_day": v["launches_per_day"],
 "launcher": "POSM multicall 1,444 bytes, 2.4333285 ETH, fresh wallet per launch (1843 wallets)",
 "first_buy": "bot router 0x1cbaf24d c1120e3d at +8/+9/+10 (p10/50/90; +6..+130), 0.0495/0.175/0.25 ETH, 31 sender wallets, in 1842/1843; before it the dust bot (+2..+3) and the decoys 0x65050a9b",
 "pull": "80.4% within 3000; from launch 11/13/127; after the bot buy 3/3/117 (3 blocks in 1044, 2-4 in 1159); launch wallet via the router a0f7978d",
 "outsiders": f"decoys in 1128 pools (0.00002-0.005 ETH); trap calibration: with our real relay buy at +1 (1048 pools) the pull is 3 blocks after the bot buy in 1040/1048 vs 119/436 without (quick-pull hours coincide with our trading hours), never before the bot buy",
 "front_rule": rs(v["front"]) + f"; live window Oct 10 09:08-11:40 (409 pools): mean +{100*C['live_window']['mean']:.2f}%, median +{100*C['live_window']['median']:.2f}%, win {100*C['live_window']['win']:.1f}% = the live record (+14.1%): pricer calibrated. The shortfall over the whole window is 229 pools (Oct 10 12h+) where the decoys buy 0.0025-0.005 ETH ahead and our 0.0058 pushes the bot buy under its 0.99 minOut (dropped: ~0%)",
 "follow_rule": rs(v["follow"]) + " (trap: the pull 3 blocks after the bot buy)",
 "capacity": "minOut decoded (word 4) = 0.99 x launch quote; room from the launch state 0.0124/0.0127/0.0129 ETH, left after others p10 0.0053",
 "engine_config": "already traded (front)", "verdict": "control-known", "candidate_score": 0,
 "notes": "control: the pricer reproduces the live +14%"})
out.append({
 "key": "operator-A (77 pools, 67 strict families, launcher 0x3194e326)", "known": "operator-A (control)", "count": a["count"], "launches_per_day": a["launches_per_day"],
 "launcher": "operator A launcher 0x3194e326 2fcb9108",
 "first_buy": "crowd (UR 1,124 bytes, 10 wallets) first real buy at +24/+54/+66, 0.0143/0.0547/0.1203 ETH, in 75/77",
 "pull": "85.7% within 3000; from launch 51/224/2180; after the first crowd buy 6/165/2157; launch wallet via POSM dd46508f",
 "outsiders": "none of real size before the crowd in the window", "front_rule": rs(a["front"]) + "; wait-150: " + rs(a["front_wait"]),
 "follow_rule": rs(a["follow"]) + " (handoff: +2-4%: calibrated)", "capacity": "crowd minOut = 0.95 x fill (fresh); room 0.043/0.059/0.089 ETH",
 "engine_config": "already traded (follow)", "verdict": "control-known", "candidate_score": 0, "notes": "control"})
json.dump({"families": out}, open(os.path.join(HERE, "families_out.json"), "w"), indent=1)
print(json.dumps({"families": out})[:200], len(json.dumps(out)))
