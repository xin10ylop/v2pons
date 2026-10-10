"""analyse_19 final: the structured per-family records (from stats.json, postwindow.json and the calldata reads in analyse.out) -> results.json"""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "stats.json"))); PW = json.load(open(os.path.join(HERE, "postwindow.json")))
K = json.load(open(os.path.join(HERE, "keys.json")))
C = S["controls"]


def fr(s):
    if not s.get("n"): return "n 0"
    return (f"n {s['n']}, mean {100*s['mean']:+.2f}%, median {100*s['median']:+.2f}%, win {100*s['win']:.0f}%, pulled-first {s['pulled_first']}, "
            f"${s['usd_trade']:+.3f} a trade, ${s['usd_day']:+.2f} a day at {s['trades_day']}/day")


def pw(k):
    ps = [v for v in PW["pools"].values() if v["family"] == k]
    return (f"to the chain head (block {PW['head']}, {min(p['blocks_to_head'] for p in ps):,}-{max(p['blocks_to_head'] for p in ps):,} blocks after the launches): "
            f"{sum(p['pulls'] for p in ps)} pulls ever, {sum(p['swaps'] for p in ps)} swaps ever, {sum(p['swaps_after_3000'] for p in ps)} after +3000")


CAL = (f"Method calibrated on the controls with the same code: vbot-v2.433 front (sell one block after the bot router's first buy) {fr(C['v2433_front_all'])}; "
       f"in the live window Oct 10 09:07-11:39 {fr(C['v2433_front_livewindow_oct10_0907_1139'])} (live: +14.1% at $15); the pricer reproduces our 1,080 live relay round trips "
       f"(model mean {100*C['live_relay_calibration']['model_mean']:.3f}% vs real {100*C['live_relay_calibration']['real_mean']:.3f}%, all 1,080 within 0.5 pt); "
       f"v2.433 capacity from the bot's calldata minOut p10/50/90 {C['v2433_capacity_p10_50_90']} ETH; operator A follow {fr(C['opA_follow'])}.")

fam = []
k = K[0]; s = S[k]
fam.append({"key": k, "known": "none", "count": 6, "launches_per_day": 3.0,
 "launcher": "imortal.buzz user-token launchpad. One wallet 0x06cb3a68 (nonces 2301-2310) calls launch contract 0xdc416cab (19,032 bytes, code hash ecd85121; 14 launches through it in the window, 6 at 804 bytes) with 7fde822e, value 0, gas 1.7M, priority 0. Calldata = name/symbol (e.g. ponsguys/PONSGUYS), an imortal.buzz IPFS URI, website, Telegram, platform address 0x94dddbb5 (words 7 and 9), 2500 (word 8), 1.7e18 (word 10). The contract mints itself a single-sided token range [132800, 201800] (L 3.2156e22, tick0 201800): no ETH in, no buy in the launch tx. All 6 launched Oct 10 17:25-18:10 UTC, 5-20 min apart. The same wallet launched all 454 7fde822e pools in the window (227/day) through 23 such contracts, about 20 launches each; the strict key splits them by metadata length.",
 "first_buy": "First non-launch buy in 6/6 pools: the chain-wide dust bot 0xe71a69f4 (one recurring wallet, not fresh) via the Universal Router execute 3593564c. Offset +3/+3/+3 (p10/50/90), size 2e-6 ETH. No buy >= 0.0002 ETH in any pool within 3,000 blocks or up to the chain head, so 0/6 pools have a scheduled buy. Over the deployer's 454 pools: 5 have a buy >= 0.0002 (0.0012-0.0107 ETH at +3, +843, +959, +1510, +1625) from 5 different outside wallets, and none from the launch wallet.",
 "pull": "0/6 pulled within 3,000 blocks; " + pw(k) + ". Nobody pulls: 0 of the deployer's 454 pools were pulled within 3,000 blocks.",
 "outsiders": "The dust bot (2e-6 ETH at +3) buys in 6/6 pools. 0 pools have a real-size outsider. There are no pulls, so the trap test has nothing to compare: pull delay after an outsider n/a (0 pulled of 6), without an outsider n/a (0 pools).",
 "front_rule": fr(s["front"]) + ". There is no scheduled buy, so every trade sells at launch+20 into an unchanged pool: two 1% fees plus gas (gross -1.99%).",
 "follow_rule": "n 0: no buy >= 0.0002 ETH in any of the 6 pools. The deployer's wider 454 pools: " + fr(S[[x for x in S if x.startswith("WIDER deployer 0x06cb3a68")][0]]["follow"]) + " (no next buy within 4 blocks).",
 "capacity": "n/a: no scheduled buy. The minOut slack of a hypothetical first buy cannot be measured.",
 "engine_config": "Not tradeable: no scheduled buy, no pull, no crowd. For reference, the recogniser would be: from 0x06cb3a68, selector 7fde822e, value 0, calldata 740-932 bytes to any of its ~19 KB launch contracts; fee 10000, ts 200, hooks 0, single-sided [132800, 201800].",
 "verdict": "no-schedule", "candidate_score": 0,
 "notes": "Launchpad (user tokens, liquidity stays in the contract-owned range), not a pump-and-pull operator. Both trading rules lose about 2% a trade on fees alone. " + CAL})

k = K[1]; s = S[k]
fam.append({"key": k, "known": "none", "count": 6, "launches_per_day": 3.0,
 "launcher": "The same imortal.buzz launchpad and the same single wallet 0x06cb3a68 (nonces 2216-2233). Launch contract 0xe43be69c (19,028 bytes, code hash 4eaf3ea3; 20 launches through it in the window at 740/772/804 bytes) is called with 7fde822e, value 0, gas 1.66M, priority 0. Calldata: name/symbol (e.g. BASKET INU/BINU), imortal.buzz IPFS URI, platform 0x94dddbb5, 2500, 1.7e18. Single-sided token range [132800, 201800], L 3.2156e22. All 6 launched Oct 10 02:21-03:46 UTC, 5-35 min apart.",
 "first_buy": "First non-launch buy in 6/6 pools: the dust bot 0xe71a69f4 via the Universal Router. Offset +2/+3/+3, size 2e-6 ETH. No buy >= 0.0002 ETH within 3,000 blocks or up to the chain head, so 0/6 pools have a scheduled buy.",
 "pull": "0/6 pulled within 3,000 blocks; " + pw(k) + ". Nobody pulls.",
 "outsiders": "The dust bot buys in 6/6 pools. 0 pools have a real-size outsider. With no pulls the trap test is n/a: 0 pulled after an outsider, and no pools without one.",
 "front_rule": fr(s["front"]) + ". There is no scheduled buy, so every trade sells at +20 into an unchanged pool: two 1% fees plus gas.",
 "follow_rule": "n 0: no buy >= 0.0002 ETH.",
 "capacity": "n/a: no scheduled buy.",
 "engine_config": "Not tradeable. Same recogniser as the 0xdc416cab family: deployer 0x06cb3a68, 7fde822e, value 0, fee 10000, ts 200.",
 "verdict": "no-schedule", "candidate_score": 0,
 "notes": "The same launchpad as the first family, split only by launch contract and metadata length. It behaves the same way: no schedule, no pull, about -2% a trade."})

k = K[2]; s = S[k]; W = S[[x for x in S if x.startswith("WIDER launch contract 0x0000ffff")][0]]
fam.append({"key": k, "known": "none", "count": 5, "launches_per_day": 2.5,
 "launcher": "Public launchpad contract 0x0000ffff (vanity address, 4,127 bytes, code hash 4a586d92). Its multicall ac9650d8 holds [dec14be1 deploy a token (1e9 supply; name, symbol, description, IPFS image, e.g. 'Fly #9'/FLY9), b6982b48 create the v4 pool: the PositionManager mints a single-sided token range [-160100, 198050] at tick0 198050, L 5.0074e22, fee 2500, ts 25, hooks 0]. Value 0, gas 3.3M, priority 1 wei. Of the 5 launches, 4 come from 0x26e8134e (nonces 63496-63502, all 4 within 0.4 min on Oct 9 23:53 UTC; a very busy wallet that also launches 274 hooked pools through 0xfcd18241, 120 of them pulled, which are other families) and 1 from 0x5a617b5f (nonce 0, Oct 9 16:59). The contract in all: 66 pools, 36 deployers, 33/day, calldata 260-3236 bytes, launch values 0/0.005/1.5 ETH.",
 "first_buy": "First non-launch buy in 5/5 pools: the dust bot 0xe71a69f4 via the Universal Router. Offset +3/+3/+5, size 2e-6 ETH. No buy >= 0.0002 ETH within 3,000 blocks, so 0/5 pools have a scheduled buy. After the window, 4/5 pools get one buy of 0.00076-0.00139 ETH at +102,486..+102,619 blocks: the 4 pools launched together, so these 4 buys land within 13 s of each other about 2.9 h later. That is one sweeper, not a schedule. Across the launchpad's 66 pools, 17 have a real first buy at +31/+198/+889 (p10/50/90) of 0.0004/0.099/0.18 ETH from 17 different wallets (4 of them the launch wallet).",
 "pull": "0/5 pulled within 3,000 blocks; " + pw(k) + ". 0 of the launchpad's 66 pools were pulled within 3,000 blocks, although they took 32.4 ETH of buys: the liquidity stays.",
 "outsiders": "The dust bot buys in 5/5 pools; 0 pools have a real outsider before any scheduled buy. With no pulls the trap test is n/a.",
 "front_rule": fr(s["front"]) + ". Every trade sells at +20 with no buy in between: two fees (2899 = 2500 + 399 protocol fee in 4 pools, 2500 in 1) plus gas. The whole launchpad (66 pools): " + fr(W["front"]) + ".",
 "follow_rule": "n 0 in the family. The whole launchpad (66 pools): " + fr(W["follow"]) + "; 1 of 17 positive: organic buyers, no crowd behind the first buy.",
 "capacity": "n/a for the family (no scheduled buy). The launchpad's 17 first real buys, with minOut ASSUMED at 0.99 x the launch-state quote (13 go through the Universal Router execute, which is nested and not decoded; 4 through other routers): p10/50/90 0.0127/0.0202/0.0207 ETH ahead.",
 "engine_config": "Not tradeable. Recogniser for reference: to 0x0000ffffbe8efe702c8703ae3477ff5de3d319c0, ac9650d8 (or b6982b48), fee 2500, ts 25, hooks 0, tick0 198050, single-sided [-160100, 198050].",
 "verdict": "no-schedule", "candidate_score": 0,
 "notes": "A public token launchpad with many deployers and locked-looking liquidity. No pulls in 66 pools, no scheduled buys, organic first buys at random offsets. Neither front nor follow has an edge here (front -0.6% on this family's 0.25% fee, follow -0.18% on the whole launchpad)."})

k = K[3]; s = S[k]; W = S[[x for x in S if x.startswith("WIDER selector f03e0011")][0]]
fam.append({"key": k, "known": "none", "count": 5, "launches_per_day": 2.5,
 "launcher": "One wallet 0xf3bce9e9 (nonces 0-20) calls its own launch contract 0x038ed9c7 (23,941 bytes, code hash f91f9868) with f03e0011(name, symbol, ...), 292-byte calldata (e.g. hoooff/HOOOFF), gas 2.45M, priority 0. Value 1e-5 ETH (one launch 1e-6) is a dev buy inside the launch tx: 9.875e-6 ETH reaches the pool. Pool: fee 0, ts 200, hook 0x0025115d, which takes 1.25% of the ETH in (measured: a 40,280,189-gwei Universal Router buy shows a0 = 39,776,686.6 gwei). The PositionManager mints a single-sided token range [-887200, -74200] (L 4.08e16; one launch [-887200, -152400], L 2.04e18). 5 launches Oct 9 16:29-22:43 UTC, 20-250 min apart. A sibling contract 0x34c0d66f with hook 0xbba868de (same calldata, 7 pools, by 0xf3bce9e9 and 0x9b68dccb) takes the f03e0011 group to 12 pools, 6/day.",
 "first_buy": "Non-launch buys within 3,000 blocks in 1/5 pools: +494, 3.98e-5 ETH, from the launch wallet itself via the Universal Router. None >= 0.0002 ETH, so 0/5 pools have a scheduled buy. After the window, the launch wallet buys 4e-5..8e-5 ETH (+3404..+7034) and sells it all back (+19,828..+207,016) in 4 of 5 pools: its own tiny round trips. The f03e0011 group: 2/12 pools with a buy >= 0.0002 (0.0004 ETH at +261 and +1531, both by the launch wallet 0x9b68dccb).",
 "pull": "0/5 pulled within 3,000 blocks; " + pw(k) + ". 0 of the 12 f03e0011 pools were pulled within 3,000 blocks.",
 "outsiders": "No outsider buys in any of the 5 pools: nobody, not even the dust bot, trades them. With no pulls the trap test is n/a. The f03e0011 group: 1 outsider in 12 pools (0x8ddceeca, 0.00018 ETH at +40), never pulled.",
 "front_rule": fr(s["front"]) + ". There is no buy before the +20 sell. The 0% LP fee is replaced by the hook's 1.25% on the ETH in (measured) and an ASSUMED 1.25% on the ETH out, plus gas. The f03e0011 group (12): " + fr(W["front"]) + ".",
 "follow_rule": "n 0 in the family. The f03e0011 group: " + fr(W["follow"]) + ".",
 "capacity": "n/a: no scheduled buy.",
 "engine_config": "Not tradeable. Recogniser for reference: from 0xf3bce9e9 to 0x038ed9c7, f03e0011, 292 bytes, value 1e-5, fee 0, ts 200, hook 0x0025115d (1.25% ETH tax).",
 "verdict": "no-schedule", "candidate_score": 0,
 "notes": "A hobby or test launcher (nonces 0-20, dev buys of $0.03) with a taxing hook. No market, no schedule, no pull. Too few launches to matter even if it had a pattern."})

ctl = [
 {"key": "CONTROL vbot-v2.433: 0x58daec31|ac9650d8|1444|2500|50|true value 2.4333285", "known": "vbot-v2.433", "count": 1843, "launches_per_day": 921.79,
  "launcher": "PositionManager multicall, value 2.4333285 ETH, one fresh wallet per launch (1,843 deployers, nonces 3-11).",
  "first_buy": "The bot router's (0x1cbaf24d c1120e3d) first buy is in 1842/1843 pools at +8/+9/+10, sized 0.0495/0.175/0.25 ETH, from 31 wallets (not fresh). The first non-launch buy of any size is the dust bot or the 0x65050a9b decoys at +2/+3/+3.",
  "pull": "1482/1843 (80%) pulled within 3,000 blocks, all by the launch wallet. Offset from launch +11/+13/+127. Offset after the bot's buy +3/+3/+117.",
  "outsiders": "Decoys and dust in 1281 pools; no real outsider (0 pools).",
  "front_rule": fr(C["v2433_front_all"]) + " (live window: " + fr(C["v2433_front_livewindow_oct10_0907_1139"]) + ")",
  "follow_rule": "Not this operator's pattern: the bot's own buy is the trigger, and the pull comes 3 blocks later.",
  "capacity": f"From the bot's calldata minOut (word 4): {C['v2433_capacity_p10_50_90']} ETH p10/50/90; minOut/quote {C['v2433_minout_over_quote_p10_50_90']}.",
  "verdict": "control-known", "candidate_score": 0, "notes": CAL},
 {"key": "CONTROL operator-A: launcher 0x3194e326 2fcb9108", "known": "operator-A", "count": 77, "launches_per_day": 38.51,
  "launcher": "Launcher 0x3194e326, a fresh wallet per launch (nonce 0), fees vary.",
  "first_buy": "The first real buy (Universal Router) is in 75/77 pools at +24/+54/+66, sized 0.014/0.055/0.12 ETH, from 10 crowd wallets.",
  "pull": "66/77 pulled within 3,000 blocks, all by the launch wallet. Offset +51/+224/+2180 from launch.",
  "outsiders": "Only dust before the crowd.",
  "front_rule": fr(S["CONTROL operator-A (every launch)"]["front"]),
  "follow_rule": fr(C["opA_follow"]),
  "capacity": "Universal Router: nested, not decoded. ASSUMED 0.99 x quote: " + str(S["CONTROL operator-A (every launch)"]["capacity"]["cap_eth_p10_50_90"]),
  "verdict": "control-known", "candidate_score": 0, "notes": "follow calibrates: the live record is about +2-4% a trade."}]
json.dump({"families": fam, "controls": ctl, "stats_file": os.path.join(HERE, "stats.json"), "postwindow_file": os.path.join(HERE, "postwindow.json")},
          open(os.path.join(HERE, "results.json"), "w"), indent=1)
for f in fam: print(f["key"], "|", f["front_rule"][:140])
print(CAL)
