"""Assemble results.json (the structured output) from stats.json, context.json, hookcheck.json, calib.json."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "stats.json"))); C = json.load(open(os.path.join(HERE, "calib.json")))
X = json.load(open(os.path.join(HERE, "context.json"))); HC = json.load(open(os.path.join(HERE, "hookcheck.json")))
K = json.load(open(os.path.join(HERE, "keys.json")))
D = json.load(open(os.path.join(HERE, "rows.json")))["rows"]


def rule(s, extra=""):
    if not s.get("n"): return f"n 0 ({s.get('exits')})" + extra
    return (f"n {s['n']}, mean {100*s['mean']:+.2f}%, median {100*s['median']:+.2f}%, win {100*s['win']:.1f}%, pulled-first {s['pulled_first']}, "
            f"${s['usd_trade']:+.3f} a trade, ${s['usd_day']:+.2f} a day ({s['trades_day']} trades/day; exits {s['exits']})" + extra)


def pct(v): return "/".join(str(x) for x in v) if v else "none"


CAL = (f"Pricer = analyse_13/common13.py (exact replay of explore/chk/replay.py) + an ETH-side hook tax; calib.py re-run here: our {C['vbot-v2.433']['n']} live v2.433 "
       f"relay trades re-priced with median |error| {C['vbot-v2.433']['abs_diff_median']:.1e}, {C['vbot-v2.433']['within_0.5pt']}/{C['vbot-v2.433']['n']} within 0.5 pt; "
       f"operator A {C['operator-A']['within_0.5pt']}/{C['operator-A']['n']} exact.")
fams = []
# ---------------- family 1: POSM 2020 fee 9000
o = S[K[0]]; ctx = X["posm_2020"]
fams.append({
    "key": K[0], "known": "none (not an operator: 6 unrelated wallets using the POSM multicall, the Uniswap-interface create+mint path)", "count": o["count"],
    "launches_per_day": o["launches_per_day_window"],
    "launcher": f"6 different EOAs (0x5e8e480c twice; nonces {pct(o['nonces'])} p10/50/90) call the PositionManager multicall ac9650d8, 2,020 bytes, values 0 to 0.030 ETH "
                f"(0, 0.000434, 0.002085, 0.00215, 0.002729, 0.003959, 0.030026), fee 9000 (0.9%), ts 90, no hooks; every pool has its own price (tick0 -159519..184110) and "
                f"one concentrated range (2 of 7 wholly above the price = ETH-only, no buy can fill; 1 wholly below); launches spread over {o['active_span_days']} d "
                f"(gaps {pct(o['gap_blocks_p10_50_90'])} blocks). The whole POSM 2020-byte class is {ctx['pools']} pools from {ctx['launchers']} wallets on {ctx['fee_tiers']} fee tiers: a retail UI path, not a bot",
    "first_buy": f"first non-launch buy: the chain-wide dust bot 0xe71a69f4 (2e-6 ETH via the Universal Router) at +3/+3/+3/+3/+4 in 5/7 (its only swap there), no swap at all in 1/7; "
                 f"the only buy >= 0.0002 ETH in the family: 1/7 pools (0x71878459), 0.00022 ETH at +1204 by 0xbd477eee (nonce 5251) via 0x076b3601 bd6858d6 (after a 0.000226 ETH sell at +458). No scheduled buy",
    "pull": f"{o['pull']['pulled']}/7 pulled within 3,000 blocks (pool 0x9c53e6d8, +1350, the launch wallet via POSM dd46508f, full range, nobody had bought but the dust bot)",
    "outsiders": "no scheduled buy, so no 'before' set; no real-size buyer before +1204 in any pool; trap test not possible (1 pull, no outsider before it)",
    "front_rule": rule(o["front"], "; nothing comes by +20: two 0.9% fees + gas into an untouched pool (2 of 7 cannot be bought at all: liquidity only above the price)"),
    "follow_rule": rule(o["follow"], "; the one trigger (0.00022 ETH at +1204) has no follow-up buy: sold at our buy + 4 for the fees"),
    "capacity": "n/a: no scheduled buy (the one +1204 buy's pool had no buyable liquidity at the launch state; its router bd6858d6 was not decoded)",
    "engine_config": "none: no schedule, no exit trigger",
    "notes": "Retail pool creations through the Uniswap PositionManager at a custom 0.9% tier; no operator structure (different wallets, prices, ranges and values; no own buys; no pull pattern). " + CAL,
    "verdict": "no-schedule", "candidate_score": 0})
# ---------------- family 2: launchpad 0xc763b179 1828
o = S[K[1]]; ctx = X["launchpad_c763b179"]
hc = "; ".join(f"{h['pid']} buy {h['hook_buy_ppm']/1e4:.2f}% / sell {h['hook_sell_ppm']/1e4:.2f}% (re-priced round trip {h['rel_err']:+.0e})" for h in HC)
fams.append({
    "key": K[1], "known": f"none (a fragment of the 0xc763b179 launchpad: {ctx['pools']} pools from {ctx['launchers']} wallets in the census, 143 in the 1796-byte family analysed by analyse_1)",
    "count": o["count"], "launches_per_day": o["launches_per_day_window"],
    "launcher": "contract 0xc763b1795dabe2d2336eba214d16969ebc5db27f selector f0e9eabf, 1,828 bytes, value 0, called by 4 wallets (0x4c43b265 x4 at nonces 413-417 within 20 min, "
                "0xc8b496f1 nonce 3, 0x4aca5305 nonce 1, 0x6752f712 nonce 4); it creates the token and a pool with fee 10000, ts 200, hook 0xae4c0cf7 (a tax hook), "
                f"tick0 206000, one range [-887200, 206000] L 33650419535429787584929 (token-only, ~1.1 ETH virtual depth). Launches over {o['active_span_days']} d, gaps {pct(o['gap_blocks_p10_50_90'])} blocks",
    "first_buy": f"first non-launch buy in {o['first_any']['pools']}/7 pools at +{pct(o['first_any']['rel'])} (p10/50/90; exact: +5, +5, +8, +943), {pct(o['first_any']['eth'])} ETH, all through the "
                 "launchpad router 0xf0b7eaaf (39ecce49, 1,060 bytes, tx value 0.0015 ETH of which the router keeps 1% and the hook 4-17%); the three early ones are one wallet "
                 "0x01e28256 (nonces 194-203) in the 3 of 4 pools of launcher 0x4c43b265, the +943 one 0x1e467dfd (nonce 4095). Across the launchpad, 4 recurring wallets "
                 f"(0x01e28256, 0x1252e24d, 0xe77716ac, 0x01cc6f2e) make the first buy in {ctx['pools_with_real_buy']}/{ctx['pools']} pools at +{pct(ctx['first_real_rel_p10_50_90'])}, "
                 f"{pct(ctx['first_real_eth_p10_50_90'])} ETH, spread over every launcher (not paired to one): a sniper/seed buyer, not a scheduled operator buy; it sells its bag later "
                 "(+316, +162, +137 here)",
    "pull": f"0/7 pulled within 3,000 blocks (0/{ctx['pools']} across the launchpad); the early buyer exits by selling its tokens instead",
    "outsiders": "no other buyer before the early buy in any pool (0 of 4 with any outsider, real or dust); no pulls at all, so the trap test has nothing to time",
    "front_rule": rule(o["front"], f". Pools with the early buy by +19 (sold one block after it, +6/+6/+9): {rule(o['front_with_sched'])}. "
                  f"The hook tax is in the price (per pool from receipts: {hc}; 4% assumed for the 3 untraded pools). With the hook tax set to 0 it is still "
                  f"{rule(o['front_nohook'])}: the early buy is 0.0012-0.0014 ETH into ~1.1 ETH of depth (+0.2%) against two 1% fees"),
    "follow_rule": rule(o["follow"], f"; with the hook tax at 0: {rule(o['follow_nohook'])}. No second buy follows, so every trade sells at our buy + 4"),
    "capacity": "decoded: the router's 39ecce49 calldata word 1 is the minOut: 1 wei in the 3 early buys (no slippage limit: unlimited room ahead), 0.606 x the launch quote "
                "in the +943 buy (0.326 ETH of room from the launch state). The early buys got exactly the launch-state quote (ratio 1.000)",
    "engine_config": "recognizer would be: to 0xc763b1795dabe2d2336eba214d16969ebc5db27f, sel f0e9eabf, len 1796/1828/1860..., value 0; eligibility fee 10000, ts 200, hook 0xae4c0cf7; "
                     "exit trigger: a buy via router 0xf0b7eaaf (39ecce49) from 0x01e28256/0x1252e24d/0xe77716ac at +3..+9. Not worth building: the hook taxes 4-17% each way",
    "notes": "The only near-schedule here is a sniper/seed wallet set that buys ~$3-9 at +5 in about half the launchpad's pools and dumps later; there is no pull, and the pool's "
             "hook charges 4-17% on each side (verified by re-pricing the early buyer's own round trips exactly from receipts: hookcheck.json). Unprofitable by 10-20 points "
             "with the tax, and still -1.8% without it. The rate our +1 buy would pay is not observable (no archive state): each pool is priced at the rate its first buy paid, which varies by pool (4% to 16.9%, not monotonic in time since launch). " + CAL,
    "verdict": "unprofitable", "candidate_score": 0})
# ---------------- families 3, 4: the 0x06cb3a68 7fde822e operator's fragments
ctx = X["op_06cb3a68"]
for key in (K[2], K[3]):
    o = S[key]; to = key.split("|")[0]
    fams.append({
        "key": key, "known": f"none (a fragment of the 0x06cb3a68 7fde822e pool-spam operator: {ctx['pools']} pools on {ctx['launch_contracts']} launch contracts / {ctx['families']} strict families "
                            f"in the census, ~{ctx['per_day']} a day, none pulled, {ctx['pools_with_real_buy']} with any buy >= 0.0002 ETH in 3,000 blocks)",
        "count": o["count"], "launches_per_day": o["launches_per_day_window"],
        "launcher": f"EOA 0x06cb3a6841c92525e7a1998328e7c9d37e98d937 (the only sender, nonces {pct(o['nonces'])}) calls its contract {to} selector 7fde822e, 804 bytes, value 0; "
                    f"fee 10000, ts 200, no hooks, tick0 201800, one token-only range [132800, 201800] L 32156000099526845215062 (no ETH in the pool); all 7 in "
                    f"{o['active_span_days']} d (gaps {pct(o['gap_blocks_p10_50_90'])} blocks; the wallet launches every ~2,920 blocks and rotates to a new contract every ~7-30 launches)",
        "first_buy": f"the only swap in every pool is the chain-wide dust bot 0xe71a69f4 (2e-6 ETH via the Universal Router) at +{pct(o['first_any']['rel'])}; no buy >= 0.0002 ETH "
                     "in 0/7 pools within 3,000 blocks; no scheduled buy",
        "pull": "0/7 pulled within 3,000 blocks (0 of the operator's 454)",
        "outsiders": "none (no buyer but the dust bot); no pull, so no trap test possible",
        "front_rule": rule(o["front"], "; nothing comes by +20 (or by +3,000): two 1% fees + gas on an untouched pool"),
        "follow_rule": rule(o["follow"], "; nothing to follow"),
        "capacity": "n/a (no scheduled buy)",
        "engine_config": f"none: recognizer would be to {to} sel 7fde822e len 804 value 0 from 0x06cb3a68, but there is no exit trigger",
        "notes": "Pool spam: single-sided token pools at a fixed price that nobody (the operator included) trades within 5 minutes; same as the other 7fde822e fragments (analyse_5/7/13). " + CAL,
        "verdict": "no-schedule", "candidate_score": 0})
# ---------------- controls
o = S["control:vbot-v2.433"]
fams.append({
    "key": "control:vbot-v2.433 (0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true, value 2.4333285 ETH)", "known": "vbot-v2.433 (control)",
    "count": o["count"], "launches_per_day": o["launches_per_day_window"],
    "launcher": "a fresh wallet per launch (1,843 senders, nonces 3/10/11) calling POSM multicall with exactly 2.4333285 ETH; fee 2500, ts 50, one sqrtP and liquidity for all",
    "first_buy": f"first non-launch buy (any size): the dust bot / the decoys at +{pct(o['first_any']['rel'])}; the scheduled buy (router 0x1cbaf24d c1120e3d) in {o['sched']['pools']}/1843 at "
                 f"+{pct(o['sched']['rel'])}, {pct(o['sched']['eth'])} ETH (p10/50/90), from {o['sched']['n_from']} recurring wallets (nonces {pct(o['sched']['from_nonce'])})",
    "pull": f"{100*o['pull']['frac']:.1f}% pulled within 3,000 blocks, +{pct(o['pull']['rel'])} after launch, +{pct(o['pull']['from_sched'])} after the bot's buy; all by the launch wallet "
            "through the router a0f7978d",
    "outsiders": f"real outsiders (>= 0.0002 ETH, not the dust bot or decoy routers) before the bot's buy: {o['trap']['pools_with_real_outsider_before_sched']} pools; any-size (dust/decoys): {o['trap']['any_outsider_pools']}",
    "front_rule": rule(o["front"], f"; p10/50/90 {pct(o['front']['p10_50_90'])}; 229 pools where our 0.0058 ahead makes a small bot buy fail its minOut (no sell-into)"),
    "follow_rule": rule(o["follow"], " (the pull comes 3 blocks after the bot's buy)"),
    "capacity": f"real minOut (word 4) = 0.99 x the launch quote: {pct(o['cap']['cap_from_launch'])} ETH ahead from the launch state (p10/50/90), {pct(o['cap']['room_left'])} left at the chain state",
    "engine_config": "live (front)", "notes": "calibration control: median +14.0% (mean +11.9%) matches the live audit's +14%; " + CAL, "verdict": "control-known", "candidate_score": 0})
o = S["control:operator-A"]
VALS = "%s-%s ETH" % (min(r["value"] for r in D["control:operator-A"]), max(r["value"] for r in D["control:operator-A"]))
fams.append({
    "key": "control:operator-A (launcher 0x3194e32622c5d860a0572c74edda99dcfd8fc827 and its per-launch copies)", "known": "operator-A (control)",
    "count": o["count"], "launches_per_day": o["launches_per_day_window"],
    "launcher": "fresh wallets (nonce 0) through the launcher 2fcb9108 (or its per-launch copies), values " + VALS,
    "first_buy": f"first non-launch buy: the dust bot at +{pct(o['first_any']['rel'])}; the first real (crowd) buy in {o['first_real']['pools']}/77 at +{pct(o['first_real']['rel'])}, "
                 f"{pct(o['first_real']['eth'])} ETH via the Universal Router, {o['first_real']['n_from']} crowd wallets",
    "pull": f"{100*o['pull']['frac']:.1f}% pulled within 3,000 blocks, +{pct(o['pull']['rel'])} after launch, +{pct(o['pull']['from_sched'])} after the first crowd buy; all by the launch wallet via POSM dd46508f",
    "outsiders": f"real outsiders before the crowd: {o['trap']['pools_with_real_outsider_before_sched']} pools",
    "front_rule": rule(o["front"], " (the crowd comes after the +20 deadline)"),
    "follow_rule": rule(o["follow"]),
    "capacity": f"ASSUMED minOut 0.99 x the launch quote (UR execute nested, not decoded): {pct(o['cap']['cap_from_launch'])} ETH",
    "engine_config": "live (follow)", "notes": "calibration control: follow +4.3% matches the live +2-4%; " + CAL, "verdict": "control-known", "candidate_score": 0})
json.dump({"families": fams}, open(os.path.join(HERE, "results.json"), "w"), indent=1)
for f in fams: print(json.dumps(f)[:600]); print()
