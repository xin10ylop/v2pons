"""Assemble results.json (the structured output) from stats.json, calib.json, decode.json, fam3_variants.json, fam3_follow.json."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
S = json.load(open(os.path.join(HERE, "stats.json"))); C = json.load(open(os.path.join(HERE, "calib.json")))
V = json.load(open(os.path.join(HERE, "fam3_variants.json"))); FL = json.load(open(os.path.join(HERE, "fam3_follow.json")))
K = json.load(open(os.path.join(HERE, "keys.json")))


def rule(s, extra=""):
    if not s.get("n"): return "n 0" + extra
    return (f"n {s['n']}, mean {100*s['mean']:+.2f}%, median {100*s['median']:+.2f}%, win {100*s['win']:.1f}%, pulled-first {s['pulled_first']}, "
            f"${s['usd_trade']:+.3f} a trade, ${s['usd_day']:+.2f} a day ({s['trades_day']} trades/day)" + extra)


def pct(v): return "/".join(f"{x}" for x in v) if v else "none"


fams = []
# ---- 1 and 4: the 0x06cb3a68 7fde822e operator's fragments
for key, lo, hi in ((K[0], 2241, 2255), (K[3], 1901, 1919)):
    o = S[key]; to = key.split("|")[0]
    fams.append({
        "key": key, "known": "none (a fragment of the 0x06cb3a68 7fde822e operator: 454 pools on 27 launch contracts / 91 strict families in the census, none pulled, 0 with a buy >= 0.0002 ETH as the first buy)",
        "count": o["count"], "launches_per_day": o["launches_per_day_window"],
        "launcher": f"EOA 0x06cb3a6841c92525e7a1998328e7c9d37e98d937 (the only sender, nonces {lo}-{hi}) calls contract {to} selector 7fde822e, {key.split('|')[2]}-byte calldata, value 0; "
                    f"pool fee 10000, tick spacing 200, hooks 0, tick0 201800, one range [132800, 201800] L 32156000099526845215062; all {o['count']} launches inside {o['active_span_days']} d "
                    f"(gaps {pct(o['gap_blocks_p10_50_90'])} blocks, ~5-10 min apart)",
        "first_buy": f"no non-launch buy >= 0.0002 ETH in any pool (0/{o['count']}) within 3,000 blocks; the only buy in every pool is the chain-wide dust bot 0xe71a69f4 "
                     f"(2e-6 ETH via the Universal Router) at +{pct(o['first_any']['rel'])} (p10/50/90); one swap per pool in total",
        "pull": f"0/{o['count']} pulled within 3,000 blocks (no negative ModifyLiquidity at all)",
        "outsiders": "none: no scheduled buy and no buyer but the dust bot, so no trap test is possible",
        "front_rule": rule(o["front"], "; nothing comes by +20, so it is two 1% pool fees + gas on an untouched pool (the same at any hold up to +3,000)"),
        "follow_rule": rule(o["follow"], " (no buy >= 0.0002 ETH to follow)"),
        "capacity": "n/a (no scheduled buy)",
        "engine_config": f"not tradeable: recognizer would be to {to} sel 7fde822e len {key.split('|')[2]} value 0 from 0x06cb3a68; no exit trigger exists",
        "notes": "No operator buy, no crowd, no pull: the operator launches 1%-fee pools and nobody (itself included) trades them within 5 minutes. Same picture as the other 7fde822e fragments (analyse_5/analyse_7: 5 of 454 pools ever got a real buy).",
        "verdict": "no-schedule", "candidate_score": 0})
    if key == K[0]:
        o2 = S[K[1]]
        fams.append({
            "key": K[1], "known": "none (deployer 0x843784a6d2c839ca170e64c75dcc797dfc4a86a3: 16 pools in 3 strict families, all through 0xe181b36e, all untraded)",
            "count": o2["count"], "launches_per_day": o2["launches_per_day_window"],
            "launcher": f"EOA 0x843784a6d2c839ca170e64c75dcc797dfc4a86a3 (only sender, nonces 27-42) calls contract 0xe181b36e96e9cab0130707bcb513fc1401e0ba32 (23,627 bytes) selector a25a9a3d, "
                        f"868 bytes, value 0.000100683 ETH; fee 10000, ts 200, hooks 0, tick0 207199, one range [87200, 207200] L 25416985444112370758962; all 8 within {o2['active_span_days']} d (gaps {pct(o2['gap_blocks_p10_50_90'])} blocks)",
            "first_buy": f"no buy >= 0.0002 ETH in any pool (0/8); only the dust bot 0xe71a69f4 (2e-6 ETH, Universal Router) at +{pct(o2['first_any']['rel'])}",
            "pull": "0/8 pulled within 3,000 blocks",
            "outsiders": "none (nobody but the dust bot buys); no trap test possible",
            "front_rule": rule(o2["front"], "; untouched pool, sold at +20 for two 1% fees + gas"),
            "follow_rule": rule(o2["follow"], " (nothing to follow)"),
            "capacity": "n/a (no scheduled buy)",
            "engine_config": "not tradeable (no exit trigger)",
            "notes": "Short-lived deployer (8 launches Oct 8 21:53-23:08 UTC, 16 in all through the same contract), no activity after; nothing to front or follow.",
            "verdict": "no-schedule", "candidate_score": 0})
    if key == K[0]:
        o3 = S[K[2]]
        v20 = V["variants"]["3236+3204|buy+20|sell sched+1 cap +300"]; vfl = FL["next>=0.05|H200"]; vfl100 = FL["next>=0.01|H100"]
        fams.append({
            "key": K[2], "known": "none (the '1.5-ETH dev-buy' operator; sibling strict family 0x0000ffff...|ac9650d8|3204|2500|25|true, 2 pools, same pattern)",
            "count": o3["count"], "launches_per_day": o3["launches_per_day_window"],
            "launcher": "a fresh wallet per launch (7 senders, nonce 0) calls the launch contract 0x0000ffffbe8efe702c8703ae3477ff5de3d319c0 (4,127 bytes) multicall ac9650d8, "
                        "3,236 bytes (3,204 in the sibling), value exactly 1.5 ETH, which creates the pool AND buys 1.5 ETH in the launch tx itself; fee 2500, ts 25, hooks 0, tick0 198050, "
                        f"one range [-160100, 198050] L 50074188046840591947412; 7 launches over {o3['active_span_days']} d (gaps {pct(o3['gap_blocks_p10_50_90'])} blocks), 9 with the sibling (4.5/day)",
            "first_buy": f"first non-launch buy: the dust bot at +3 in 7/7. First real buy (>= 0.0002): 7/7 at +{pct(o3['first_real']['rel'])} (p10/50/90), {pct(o3['first_real']['eth'])} ETH; "
                         "6/7 are the 'scheduled' candidate: a round-size buy (0.16 x3, 0.2 x2, 0.18; 0.15 x2 in the sibling at +135/+139) through router 0x75379d5d2ea4c98aeaa57f32e233707550ab03f0 "
                         "(UR-style execute 3593564c, 1,540 bytes, value 0), each from a DIFFERENT high-nonce wallet (nonces 1,686-4,144) never seen in any other pool's first 8 swaps (8 wallets / 8 pools); "
                         "the 7th pool's first real buy is a 0.008 ETH sniper (0x81586f00) at +15 and it never gets the 0x75379d5d buy. Then a crowd (recurring small wallets 0x0b410a5f, 0x1a2d2cd5, "
                         "0xe9d83e95 via 0x4f881c6a, more 0x75379d5d wallets with 0.1-0.3 ETH) buys from +150 to +400; 0.3-7 ETH of buys per pool in 3,000 blocks",
            "pull": "0/7 pulled within 3,000 blocks (0/9 with the sibling; the liquidity never moves). The pull's role is taken by the launcher selling its 1.5 ETH bag: seen in the first 8 swaps "
                    "in 2/7 (+18 before the router buy, +195 in the pool that never got it, 1.494 and 1.499 ETH out); the other pools' big sells (unattributed, beyond the census' first 8 txs) "
                    "come at +462 (1.67 ETH), +1222 (2.62), +2152 (1.44), +619 (2.27, sibling) or not in the window",
            "outsiders": "no outsider of any size before the 0x75379d5d buy in the 6 pools that got it (only the dust bot). The one pool with an early real buy (0.008 ETH at +15) never got the "
                         "router buy and was dumped by the launcher at +195 (the sniper sold at +196); the +18 dump came with no outsider at all. n = 1 each: inconclusive, and there are no pulls to time",
            "front_rule": rule(o3["front"], f" (exits {o3['front']['exits']}); the router buy comes at +140..+225, after the +20 deadline, so 6 pools return -0.57% (two 0.25% fees + gas) and "
                          "the +18 launcher dump costs -61% in one. Waiting for the router buy instead (sell one block after it, +141..+226): " + rule(o3["front_wait"], f", p10/50/90 {o3['front_wait']['p10_50_90']}: "
                          "+7.5..+9.6% in 5, -56% and -61% to the two launcher dumps")),
            "follow_rule": rule(o3["follow"], "; the trigger is the router buy itself (+140..+225) and the next >= 0.0002 buy is a speck 10-60 blocks later, so it sells flat at two fees"),
            "capacity": "minOut DECODED from the 0x75379d5d calldata (commands 0x10,0x90; V4_SWAP actions 07 0b 0e = SWAP_EXACT_IN, SETTLE, TAKE; ExactInputParams amountOutMinimum = 0 in all 8 "
                        "router buys of the family and its sibling; the second command's min word is 0 too): no revert limit, any ETH can sit ahead (only our own price impact on a ~4 ETH-deep pool limits size). "
                        f"Under the 0.99 x launch-quote assumption it would be {pct(o3['capacity']['cap_from_launch_eth'])} ETH; the router buy got exactly the launch-state quote (ratio {pct(o3['capacity']['actual_over_launch_quote'])})",
            "engine_config": "recognizer: to 0x0000ffffbe8efe702c8703ae3477ff5de3d319c0, sel ac9650d8, len 3236 or 3204, value exactly 1.5 ETH, sender nonce 0; eligibility: fee 2500, ts 25, hooks 0, "
                             "tick0 198050, L 5.0074e22, a 1.5 ETH buy inside the launch tx; fire offset would have to be +20 or later (after the early-dump window), exit trigger the first buy through "
                             "0x75379d5d (0.15-0.2 ETH, minOut 0) at +135..+225, hold 120-210 blocks; a launcher sell (from = launch wallet) is the stop",
            "notes": f"Best variants (in-sample, tiny n): buy at +20..+120 and sell one block after the router buy (cap +300): {rule(v20)}, the loss is the pool with no router buy (launcher dump at +195). "
                     f"Follow-long (buy one block after the router buy, sell one block after the next buy >= 0.05 ETH or at +200): {rule(vfl)}; with >= 0.01 ETH / +100: {rule(vfl100)}. "
                     "These ride a crowd that keeps buying 150-400 blocks in, not a schedule of the operator's own (the router buyers are distinct wallets each launch), with the launcher's 1.5 ETH bag "
                     "over the position for 10-20 s; 4.5 launches a day caps it at ~$5 a day at $15. The structure the owner wants (own buy at fixed blocks with slack, pull a fixed margin after) is absent.",
            "verdict": "unprofitable", "candidate_score": 0})
# ---- controls
ov = S["control:vbot-v2.433"]; oa = S["control:operator-A"]
fams.append({
    "key": "control:vbot-v2.433 (0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true at 2.4333285 ETH)", "known": "vbot-v2.433 (control)",
    "count": ov["count"], "launches_per_day": ov["launches_per_day_window"],
    "launcher": "a fresh wallet per launch (1,843 senders, nonce p10/50/90 3/10/11) -> POSM multicall 1,444 bytes, value 2.4333285 ETH; fee 2500 ts 50, L 4.928e22",
    "first_buy": f"first non-launch buy (any size) +{pct(ov['first_any']['rel'])}: the dust bot 940, decoy router 0x65050a9b 854, the bot router 49; the bot's router buy (c1120e3d) in 1842/1843 at "
                 f"+{pct(ov['sched']['rel'])}, {pct(ov['sched']['eth'])} ETH, from {ov['sched']['n_from']} recurring bot wallets (nonces ~37k)",
    "pull": f"{ov['pull']['pulled_3000']}/{ov['count']} ({100*ov['pull']['frac']:.1f}%) within 3,000 blocks; from launch +{pct(ov['pull']['rel'])}; from the bot buy +{pct(ov['pull']['from_sched'])}; "
            "all by the launch wallet via the bot router a0f7978d",
    "outsiders": f"no real-size outsider before the bot buy in any pool; 5 pools with specks (2e-5..5e-5 ETH): pulled 3/5, pull at bot buy +{pct(ov['outsiders']['anysize_pull_from_sched_with'])} vs "
                 f"+{pct(ov['outsiders']['anysize_pull_from_sched_without'])} without",
    "front_rule": rule(ov["front"], f", p10/50/90 {ov['front']['p10_50_90']}; sell one block after the bot buy (S +{pct(ov['front']['S_rel'])}); CALIBRATION: the replay reproduces the "
                  f"{C['vbot-v2.433']['n_priced']} live relay trades in the census (realised gross {100*C['vbot-v2.433']['real_mean']:+.2f}% vs replay {100*C['vbot-v2.433']['sim_matched_mean']:+.2f}%, "
                  f"per-trade diff p10/50/90 {pct(C['vbot-v2.433']['diff_p10_50_90'])}, all within 0.5 pt); operator A's 35 live trades reproduce exactly"),
    "follow_rule": rule(ov["follow"], " (the first real buy is the bot's; the pull lands 3 blocks later)"),
    "capacity": f"minOut from calldata word 4 = {pct(ov['capacity']['minout_over_quote'])} x the launch-state quote; ETH that fits ahead from the launch state {pct(ov['capacity']['cap_from_launch_eth'])}, "
                f"left at the chain state {pct(ov['capacity']['room_left_eth'])} (229 pools had a later bot buy dropped with our 0.0058 in front)",
    "engine_config": "live (front)", "notes": "calibration control: median +14.0% matches the live audit (+14%).", "verdict": "control-known", "candidate_score": 0})
fams.append({
    "key": "control:operator-A (launcher 0x3194e32622c5d860a0572c74edda99dcfd8fc827, 2fcb9108, and its copies)", "known": "operator-A (control)",
    "count": oa["count"], "launches_per_day": oa["launches_per_day_window"],
    "launcher": "fresh launch wallets (77 senders, nonce 0), values 1.55-2.7 ETH, fee varies",
    "first_buy": f"first non-launch buy: the dust bot at +{pct(oa['first_any']['rel'])}; first real (crowd) buy in 75/77 at +{pct(oa['sched']['rel'])}, {pct(oa['sched']['eth'])} ETH via the UR, "
                 f"{oa['sched']['n_from']} crowd wallets (0x8700722d 25, 0x295877ce 23, 0xdc2e8661 15)",
    "pull": f"{oa['pull']['pulled_3000']}/77 ({100*oa['pull']['frac']:.1f}%), from launch +{pct(oa['pull']['rel'])}, from the first crowd buy +{pct(oa['pull']['from_sched'])}, all by the launch wallet via POSM dd46508f",
    "outsiders": f"no real-size outsider before the first crowd buy; specks (4e-5..6e-5, 0xf7b47b17) in 27: pulled {100*oa['outsiders']['anysize_pulled_frac_with']:.0f}% vs {100*oa['outsiders']['anysize_pulled_frac_without']:.0f}%, "
                 f"pull after the crowd buy +{pct(oa['outsiders']['anysize_pull_from_sched_with'])} vs +{pct(oa['outsiders']['anysize_pull_from_sched_without'])}",
    "front_rule": rule(oa["front"], f" (the crowd comes after +20); waiting for it: {rule(oa['front_wait'])}"),
    "follow_rule": rule(oa["follow"]),
    "capacity": f"ASSUMED minOut 0.99 x launch quote (UR execute nested, not decoded): {pct(oa['capacity']['cap_from_launch_eth'])} ETH",
    "engine_config": "live (follow)", "notes": "calibration control", "verdict": "control-known", "candidate_score": 0})
res = {"families": fams, "files": sorted(os.listdir(HERE))}
json.dump(res, open(os.path.join(HERE, "results.json"), "w"), indent=1)
print(json.dumps({"families": fams}, indent=1))
