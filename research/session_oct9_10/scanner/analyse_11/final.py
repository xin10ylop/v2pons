"""assemble results.json (the structured output) from stats.json, calib.json, extras.json, competitor.json, postwindow.json, fam4_*.json"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common11 import fmt_rule  # noqa
J = lambda n: json.load(open(os.path.join(HERE, n)))
S, C, X, PW, V4, SL = J("stats.json"), J("calib.json"), J("extras.json"), J("postwindow.json")["per_family"], J("fam4_variant.json"), J("fam4_slack.json")
K = J("keys.json")
pct = lambda v: f"{100*v:+.2f}%"


def fr(s):
    if not s.get("n"): return f"n 0 ({s.get('pools_without_real_buy', '')} pools without a real buy)"
    return fmt_rule(s)


fams = []
# 1, 2: the 7fde822e single-wallet launchers
for i, (dep, code, rng) in enumerate((("0x970dcc45 (nonces 2-11)", "20,965 bytes, code hash 09303719", "131000..200000 (tick0 200000), L 3.99e22"),
                                       ("0xcfa921b4 (nonces 1-13)", "19,026 bytes, code hash 95b32001", "132800..201800 (tick0 201800), L 3.22e22"))):
    k = K[i]; s = S[k]; x = X[k]; pw = PW[k]
    fams.append({
        "key": k, "known": "none", "count": s["count"], "launches_per_day": s["launches_per_day_window"],
        "launcher": f"contract {k[:42]} ({code}) called with 7fde822e ({k.split('|')[2]} bytes), value 0, by ONE wallet {dep}; {x['first_launch_utc']} to {x['last_launch_utc']} UTC, "
                    f"gaps p10/50/90 {s['launch_gap_blocks_p10_50_90']} blocks. Token + single-sided LP in one call (range {rng}, fee 1%, ts 200, no hook). "
                    "Part of the 7fde822e launcher class (490 pools on 27 contracts, 5 deployers in the census; loose family 7fde822e|772: 104 pools on 25 contracts).",
        "first_buy": f"no non-dust buy in any pool: the only swap is the chain-wide dust bot 0xe71a69f4 (2e-6 ETH via the UR) at +{s['first_any_buy']['rel_p10_50_90']} (p10/50/90) in "
                     f"{s['first_any_buy']['pools']}/{s['count']} pools; 0/{s['count']} pools with a buy >= 0.0002 ETH within 3,000 blocks, and none after it up to head 85,259,924 "
                     f"({pw['blocks_after_last_launch_to_head']:,} blocks after the last launch; swaps logged ever: {pw['swaps_logged']}, all the dust bot's).",
        "pull": f"0/{s['count']} pulled within 3,000 blocks; never pulled up to head 85,259,924 (eth_getLogs of every ModifyLiquidity of the {s['count']} pools: only the launch mints).",
        "outsiders": "no buys before a scheduled buy because there is no scheduled buy; trap test not applicable (no pull ever).",
        "front_rule": f"{fr(s['front'])}. No scheduled buy, so every sell is at the launch+20 deadline: the result is two 1% pool fees + gas.",
        "follow_rule": fr(s["follow"]),
        "capacity": "n/a: no scheduled buy to sit ahead of.",
        "engine_config": "nothing to trade: no buyer, no pull.",
        "verdict": "no-schedule", "candidate_score": 0,
        "notes": "Dead token launches: nobody but the dust bot ever touches these pools. Same picture as the other 7fde822e families (analyse_7: 490 pools, front -2.06%, 0 pulls)."})
# 3: the 0x0000ffff multicall launch kit
k = K[2]; s = S[k]; x = X[k]; pw = PW[k]
fams.append({
    "key": k, "known": "none", "count": s["count"], "launches_per_day": s["launches_per_day_window"],
    "launcher": f"0x0000ffff (4,127 bytes, code hash 4a586d92) multicall ac9650d8, 1,476 bytes, value 0: a shared create-and-mint kit (about 40 wallets use it in the window, calldata "
                f"260-3,364 bytes by token metadata, so this strict key is an arbitrary slice). Deployers: 0x26e8134e x5 (nonces 63,494-63,499, a burst of 5 within 225 blocks at "
                f"84,558,109; the same high-volume wallet launches 262 hook pools through 0xfcd18241 6fe958d8 in the window), 0x6cd65489, 0x99339fd4, 0x692f74bc x1 each. "
                f"{x['first_launch_utc']} to {x['last_launch_utc']} UTC. Single-sided range -160100..198050 (tick0 198050), L 5.0e22, fee 2500 (2899 = 2500 + a 400-pip protocol fee in pools after block ~84.4M), ts 25, no hook.",
    "first_buy": f"dust only: 0xe71a69f4 2e-6 ETH at +{s['first_any_buy']['rel_p10_50_90']} in {s['first_any_buy']['pools']}/8. One pool (0x0df03e4e) has real buys, all late: "
                 "the launch wallet 0x26e8134e itself 0.000402 ETH via the UR at +1169, +1301, +1365, +1425 and one 0.0495 ETH via 0x65050a9b at +1372; 1/8 pools with a real buy. "
                 f"After the window: {pw['swaps_after_window']} swaps, all sells, no buy, up to head 85,259,924.",
    "pull": "0/8 pulled within 3,000 blocks; never pulled up to head 85,259,924.",
    "outsiders": "no scheduled buy; 0 real outsiders; trap test not applicable (no pull ever).",
    "front_rule": f"{fr(s['front'])}. Every sell at launch+20 (the one real buy is at +1169): the result is two 0.25-0.29% fees + gas.",
    "follow_rule": f"{fr(s['follow'])} (the one pool: buy after the launch wallet's 0.000402 at +1169).",
    "capacity": "n/a (the only 'first buy' is the launch wallet's own 0.000402 ETH at +1169 via the UR execute, nested, not decoded; under the ASSUMED 0.99 x launch-state quote its room would be 0.0127 ETH, meaningless here).",
    "engine_config": "nothing to trade.",
    "verdict": "no-schedule", "candidate_score": 0,
    "notes": "Generic launch-kit pools with no market. Lead for others (not this family): the wallet 0x26e8134e's 0xfcd18241 hook launches (262 pools, fees 3000/10000/30000/100000)."})
# 4: 0x387a453d, hook 0xe5e70264
k = K[3]; s = S[k]; x = X[k]
b777 = [p["b777_rel"] for p in V4["per_pool"]]
fill7 = sorted(r["b0.04777"]["fill_over_launch_quote"] for r in SL if "b0.04777" in r)
ahead7 = sorted(r["b0.04777"]["eth_bought_ahead"] for r in SL if "b0.04777" in r)
grid = V4["grid"]; gm = [v["mean"] for v in grid.values()]; gw = [v["win"] for v in grid.values()]
fams.append({
    "key": k, "known": "none", "count": s["count"], "launches_per_day": s["launches_per_day_window"],
    "launcher": f"contract 0x387a453d (4,521 bytes, code hash 10e37260) 54e231e6, 1,412 bytes, by ONE wallet 0xc0b3535e (nonces 61,703-61,794, a busy wallet), value 0.21777/0.2777/0.41655/0.69425 ETH "
                f"('777' amounts); {x['first_launch_utc']} to {x['last_launch_utc']} UTC, gaps p10/50/90 {s['launch_gap_blocks_p10_50_90']} blocks. Fee 0 + hook 0xe5e70264 (takes 4% of the output on buys "
                "AND sells, measured from receipts; the same hook as the 0x2a53386d launchpad), full-range liquidity -887200..887200, L 2.93e22 (virtual ETH reserve 4.2-4.4 ETH), "
                f"and a dev buy inside the launch tx in 8/8 pools (p10/50/90 {s['buy_in_launch_tx_eth_p10_50_90']} ETH).",
    "first_buy": f"first non-launch buy at +{s['first_real_buy']['rel_p10_50_90']} (p10/50/90; +0 once), {s['first_real_buy']['eth_p10_50_90']} ETH, in 8/8 pools, via the UR (3), 0x2a53386d f1114062 "
                 "(2, wallet 0x2c2572da nonce 155k: a launchpad sniper), 0xe0703eaa, 0x0afeb98a, 0x61e50fce; 5 distinct wallets over 8 pools, never the launch wallet. Then a sniper swarm: "
                 f"{s['real_buys_per_pool_p10_50_90']} real buys and {s['sells_per_pool_p10_50_90']} sells per pool (p10/50/90) in 3,000 blocks. The most regular buyer is 0xe7bb5145 "
                 f"(nonces 145-185) with exactly 0.04777 ETH via the UR at +{b777} in the 8 pools (7 identified by tx as 0xe7bb5145, the +6 one by its exact amount), others 0x46bab0a8 0.03, 0x20916bba ~0.002, 0xf08ad284 ~0.0025, 0x4992e7ad 0.002646; "
                 "dumps start at +3 (0x65050a9b, 0xf0b7eaaf, 0xbb75f6e4 routers; one 3.39 ETH sell at +12).",
    "pull": "0/8 pulled within 3,000 blocks and never up to head 85,259,924 (417k blocks after the last launch): the liquidity stays; exits are sells into the crowd, not pulls.",
    "outsiders": "every buyer is an outsider (dozens of wallets from +0); there is no pull to come sooner, so the trap test does not apply. The risk here is not a pull but the 8% round-trip tax and the snipers' dumps from +3.",
    "front_rule": f"(scheduled = the first real buy behind ours, at +2..+4) {fr(s['front'])}. Variant with the 0.04777 buyer as the schedule: n 8, mean {pct(V4['front_777']['mean'])}, "
                  f"median {pct(V4['front_777']['median'])}, 1/8 positive, ${V4['front_777']['usd_trade']:+.2f} a trade. Every fixed sell at launch+2..+20: mean {pct(max(gm))} at best "
                  f"(down to {pct(min(gm))}), win <= {100*max(gw):.0f}%.",
    "follow_rule": fr(s["follow"]),
    "capacity": f"not binding: the 0.04777 ETH buyer filled at {fill7[0]}-{fill7[-1]} of its launch-state quote with {ahead7[0]}-{ahead7[-1]} ETH bought ahead of it, so its minOut "
                "allows >= 12% (its calldata is a nested UR execute: not decoded). Under the ASSUMED 0.99 x launch-state quote the room ahead of the first real buy would be "
                f"{S[k]['capacity']['cap_from_launch_eth_p10_50_90']} ETH. Break-even needs ~0.175-0.184 ETH of net buying behind our buy (4% of the 4.2-4.4 ETH virtual reserve) to cover the two 4% taxes.",
    "engine_config": "not worth trading: recognizer would be to 0x387a453d, 54e231e6, 1,412 bytes, value 0.21777-0.69425, fee 0, hook 0xe5e70264; but no pull, no single scheduled buyer, 8.3% round-trip tax.",
    "verdict": "unprofitable", "candidate_score": 0,
    "notes": "A public launchpad-style market (hook tax 4%/4%, locked full-range liquidity, a dev buy in the launch tx, a sniper swarm from +0). Not the volume-bot structure. Our relay's stake would need a ~9% move in our favour within a few blocks; the snipers sell into the early buys instead."})
# controls
v = S["control:vbot-v2.433"]; xv = X["control:vbot-v2.433"]; comp = J("competitor.json")
fams.append({
    "key": "control:vbot-v2.433 (0x58daec31|ac9650d8|1444|2500|50|true, value 2.4333285)", "known": "vbot-v2.433", "count": v["count"], "launches_per_day": v["launches_per_day_window"],
    "launcher": "POSM multicall ac9650d8, 1,444 bytes, value exactly 2.4333285 ETH, a fresh wallet per launch (1,843 distinct, nonce p10/50/90 3/10/11); 10-08 18:26 to 10-10 18:20 UTC.",
    "first_buy": f"the bot's router buy (0x1cbaf24d c1120e3d) in {C['v2433_sched_rel_p10_50_90'] and 1842}/1843 pools at +{C['v2433_sched_rel_p10_50_90']} (p10/50/90), {C['v2433_sched_eth_p10_50_90']} ETH, "
                 f"from {xv['sched_from_distinct']} recurring wallets (nonces ~36.5k-39.9k, top 0x8cd2a79c 71 pools), never the launch wallet. The first non-launch buy of any size is the dust bot 0xe71a69f4 at +2..+3.",
    "pull": f"{v['pull']['pools_pulled_3000']}/1843 ({100*v['pull']['frac']:.1f}%) within 3,000 blocks, at +{v['pull']['rel_p10_50_90']} from the launch and +{v['pull']['from_sched_p10_50_90']} after the bot's buy "
            f"(3 blocks in 1,044, 4 in 101, 2 in 14); always the launch wallet, through the router a0f7978d.",
    "outsiders": f"{v['outsiders']['n_with']} of 1,842 pools have a real buy (>= 0.0002) ahead of the bot's buy, {v['outsiders']['outsider_real_eth_p10_50_90']} ETH, ALL since Oct 10 14:47 UTC "
                 f"(523 of the 587 pools launched after it): router 0xfd1b271f (EOA 0xb4c345dc) in 387 pools at +2..+3 with 0.00495 ETH, selling 0-1 blocks after the bot's buy in 355 of them "
                 "(a competing front bot), and the 0x65050a9b router from 0x488faf52 (320 pools; the handoff's decoy funder), 0x544ef435 (142), 0xe322fc6d (30), 0.00495 at +1..+2, also selling "
                 f"0-2 blocks after the bot's buy. Trap test: pull after the bot's buy with an outsider {v['outsiders']['pull_after_sched_with_p10_50_90']} vs without {v['outsiders']['pull_after_sched_without_p10_50_90']} "
                 f"(p10/50/90; pulled {v['outsiders']['pulled_with']}/{v['outsiders']['n_with']} vs {v['outsiders']['pulled_without']}/{v['outsiders']['n_without']}), {v['outsiders']['pull_after_first_outsider_p10_50_90']} blocks after the outsider: the pull does not come sooner: not a trap.",
    "front_rule": f"all: {fr(v['front'])}. CALIBRATION: before the competitors (launches < Oct 10 14:47 UTC) n 1256, mean {pct(X['v2433_front_before_1447']['mean'])}, median {pct(X['v2433_front_before_1447']['median'])}, "
                  f"win {100*X['v2433_front_before_1447']['win']:.1f}%; the live window 09:07-11:40 n 409, mean {pct(C['v2433_front_live_window_0907_1140']['mean'])}, median {pct(C['v2433_front_live_window_0907_1140']['median'])} "
                  f"(live audit: +14.1% / +16.25%); after 14:47 n 587, mean {pct(X['v2433_front_after_1447']['mean'])}: in 229 pools a competitor's 0.00495 plus our 0.0058 exceed the bot's room and its buy reverts (those trades price +0.01%).",
    "follow_rule": f"{fr(v['follow'])}: a trap (the pull 3 blocks after the bot's buy beats the next buy).",
    "capacity": f"real minOut from calldata word 4 = 0.99 x the launch-state quote (p10/50/90 {C['v2433_minout_over_quote_p10_50_90']}); room ahead of the bot's buy from the launch state "
                f"{C['v2433_cap_from_launch_p10_50_90']} ETH, left at the chain state (others ahead) {v['capacity']['room_left_at_chain_state_p10_50_90']} ETH.",
    "engine_config": "the live front: launch to POSM, ac9650d8, 1,444 bytes, value 2433328500000000000; fee 2500, ts 50, hooks 0; fire in the launch block (lands +1); sell on any buy through 0x1cbaf24d behind ours, else the +18/+20 deadline; FRONT_AHEAD_MAX_ETH 0.008.",
    "verdict": "control-known", "candidate_score": 0,
    "notes": "Pricer calibrated: +13.7% a trade on the 1,256 pools before the competitors, +14.0% in the live window (live: +14.1%); the pricer predicts 10,164 real buys from the chain's own pre-state with 0 errors over 1e-4. The competition since 14:47 UTC Oct 10 (0xfd1b271f / 0xb4c345dc and the 0x65050a9b wallets) cuts the mean to +8% and is the 'other bots doing the same thing'."})
a = S["control:operator-A"]; xa = X["control:operator-A"]
fams.append({
    "key": "control:operator-A (launcher 0x3194e326, 2fcb9108, 67 fee families)", "known": "operator-A", "count": a["count"], "launches_per_day": a["launches_per_day_window"],
    "launcher": "0x3194e326 2fcb9108 (77 pools, fee varies per launch), a fresh launch wallet per pool (nonce 0), values 1.88-2.98 ETH; 10-08 21:58 to 10-10 16:06 UTC.",
    "first_buy": f"the crowd's first real buy at +{a['first_real_buy']['rel_p10_50_90']} (p10/50/90), {a['first_real_buy']['eth_p10_50_90']} ETH, via the UR execute, from {xa['sched_from_distinct']} recurring wallets (0x8700722d 25, 0x295877ce 23, 0xdc2e8661 15), 75/77 pools.",
    "pull": f"{a['pull']['pools_pulled_3000']}/77 within 3,000 blocks at +{a['pull']['rel_p10_50_90']}, +{a['pull']['from_first_real_p10_50_90']} after the first real buy; always the launch wallet via POSM dd46508f.",
    "outsiders": "no real buy precedes the crowd's first (by construction of the first real buy); dust only (0xe71a69f4 at +3).",
    "front_rule": f"{fr(a['front'])} (front does not fit: the crowd comes at +24..+66, the deadline is +20).",
    "follow_rule": f"CALIBRATION: {fr(a['follow'])} (handoff: +2-4% a trade, none pulled since Oct 8).",
    "capacity": f"ASSUMED 0.99 x launch-state quote (UR execute nested, not decoded): {a['capacity']['cap_from_launch_eth_p10_50_90']} ETH.",
    "engine_config": "the live follow: launch to 0x3194e326 2fcb9108; trigger the first buy >= 0.0002 within 150 blocks; buy 1 block later; sell on the next real buy or at buy+4.",
    "verdict": "control-known", "candidate_score": 0,
    "notes": "Follow calibrates with the handoff (+4.3% mean here at $15, 0 pulled first)."})
json.dump({"families": fams}, open(os.path.join(HERE, "results.json"), "w"), indent=1)
print(json.dumps({"families": fams}, indent=1))
