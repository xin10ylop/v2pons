"""builds results.json (the structured per-family output) from stats.json, devsell.json, snipers.json"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "stats.json"))); SN = json.load(open(os.path.join(HERE, "snipers.json")))
K = json.load(open(os.path.join(HERE, "keys.json")))
C = S["controls"]
W1 = S[[g for g in S if g.startswith("WIDER deployer 0x841ac064")][0]]
W234 = S[[g for g in S if g.startswith("WIDER deployers of families 2-4")][0]]
WCL = S[[g for g in S if g.startswith("WIDER every POSM")][0]]
CV = S["CONTROL vbot-v2.433"]; CA = S["CONTROL operator-A"]


def rule(s, extra=""):
    if not s or not s.get("n"): return "n 0 (no trigger in any pool)" + extra
    return ("n %d, mean %+.2f%%, median %+.2f%%, win %.0f%%, pulled-first %d%s, $%+.3f a trade, $%+.2f a day (%.1f trades/day)%s"
            % (s["n"], 100 * s["mean"], 100 * s["median"], 100 * s["win"], s["pulled_first"],
               (" (+%d pulled before our buy)" % s["pulled_before_buy"]) if s.get("pulled_before_buy") else "", s["usd_trade"], s["usd_day"], s["trades_day"], extra))


fams = []
r = S[K[0]]
fams.append({
    "key": K[0], "known": "none", "count": r["count"], "launches_per_day": r["launches_per_day"],
    "launcher": "one EOA 0x841ac064763c75a6b6b916ef676420d6ffdd281f (nonces 38-52 here; all 10 of its pools nonces 2-52) calling its own token factory 0x458cdbed (15,945 bytes; the same call on 0xc7c72f08 and 0x404422f1 for 5 fee-1% pools in other families), selector d181e93a, 420-byte calldata = createToken(supply 1e27, fee word 0, tick 177284/191148, salt, name, symbol: ROBININU, The Anti-Ai Person/VAL, WASHPAD, ANTI-HARRY, OCTOBEAR); the tx value (0.01, 0.04, 0.06, 0.15, 0.2 ETH) is a dev buy executed inside the launch tx; single-sided token range [-887272, tick0], L 7.07e22 / 1.41e23. All 5 launched Oct 10 09:06-09:23 UTC (a 17-minute manual burst), none before or after in the 48 h census.",
    "first_buy": "non-launch buys in 2 of 5 pools only: +190 blocks (0.000876 ETH, wallet 0x188b9b4d nonce 36 via 0xa174f370 sel 0a2b8f36) and +2106 (0.04998 ETH, the deployer itself via 0x204faca1 UR execute); offset p10/50/90 190/190/2106, size p10/50/90 0.000876/0.000876/0.04998 ETH, 2 distinct wallets, no fresh wallet, 40% of pools; in 3 of 5 pools nobody but the deployer ever trades. Later buys at random offsets: 0.099 ETH at +1351 (0xa2192c37, nonce 44, likely the deployer's second wallet: it also buys its fee-1% pool 0x7c4907fd at +1528/+1770) and 0.00495 at +1711 (fresh 0x4a02be76, nonce 1), both via the 1%-commission router 0xf2251d75 (08c1284c, value 0.1/0.005 -> 0.099/0.00495 into the pool). No buy within launch+20 in any pool.",
    "pull": "0 of 5 pulled within 3000 blocks (no negative ModifyLiquidity at all; none in its 10 pools). The exit is the deployer SELLING its dev buy back through 0xf2251d75 (08c1284c) in 5 of 5 pools: +477, +907, +2137, +2291, +2508 blocks after launch (p10/50/90 477/2137/2508), recovering exactly its ETH (fee 0); from the first non-launch buy: +2318 (0xd95becfc, after the +190 outsider) and +185 (0xf413faf3, after its own +2106 buy).",
    "outsiders": "no buy of any size before the (non-existent) scheduled buy in any pool, dust wallet included (the 2e-6 ETH dust bot 0xe71a69f4 bought only the fee-1% pools of this deployer at +2/+3). Trap test: no pulls, so not applicable; the deployer's sell came 2318 blocks after the one outsider buy vs 477-2137 blocks after launch in the 3 pools nobody bought: no reaction.",
    "front_rule": rule(r["front"], "; nothing trades by +20 in any pool, so the fee-0 round trip returns the stake exactly and the loss is the gas (2 x 104,000 x ~0.02 gwei = $0.011). Variant selling one block after the first real buy whenever it comes (hold up to 3000): " + rule(r["front_hold3000"])),
    "follow_rule": rule(r["follow"], "; triggers +190 (0.000876) and +2106 (0.04998), no next buy within 4 blocks: deadline exits at cost minus gas"),
    "capacity": "first real buys via 0xa174f370 (0a2b8f36) and 0x204faca1 (Universal-Router execute, nested): not decoded; ASSUMED minOut = 0.99 x launch-state quote -> %s ETH ahead (p10/50/90; deep fee-0 pools). The 0xf2251d75 08c1284c buys are packed calldata: amountIn length-prefixed (0x08 016345785d8a0000 = 0.1 ETH) followed by a 1-byte field = 1 where a minOut would sit, and no field within 0.3-1.0 x the real output: effectively no minOut (layout inferred, unverified)." % (r["capacity"]["cap_eth_p10_50_90"],),
    "engine_config": "recognizer: to 0x458cdbed885a516f2e32cc5e3e9b432589fa729f, selector d181e93a, 420 bytes, value 0.01-0.2 ETH (the dev buy), from 0x841ac064; eligibility fee 0, tick spacing 1, hooks 0, single-sided range [-887272, tick0]. There is no fire offset or exit trigger to configure: no scheduled buy follows the launch (the only predictable event is the deployer's own sell, +477..+2508, which moves the price against a holder). Not tradeable.",
    "verdict": "no-schedule", "candidate_score": 0,
    "notes": "A single developer hand-launching named meme tokens with a dev buy and a zero LP fee, then selling the dev buy back 0.8-4.3 minutes later when nobody comes; its 5 fee-1%% launches through 0xc7c72f08/0x404422f1/0x458cdbed (other families) behave the same (front %s). Whole deployer (10 pools): front %s; follow %s. Fee 0 makes a round trip cost only gas, but there is nothing to sell into." % (
        "%+.2f%% each" % (100 * -0.02062), rule(W1["front"]), rule(W1["follow"]))})

for i, (k, label) in enumerate(zip(K[1:], ("20%", "25%", "50%"))):
    r = S[k]
    fb, fr, pu, tr = r["first_buy_any"], r["first_buy_real"], r["pull"], r["trap"]
    dep = ", ".join("%s" % d[0][:10] for d in r["deployers"])
    fams.append({
        "key": k, "known": "none (known_by_rule vbot-other only because the 1,444-byte POSM create-and-mint multicall is the standard layout; no bot-router buy or pull in any pool)",
        "count": r["count"], "launches_per_day": r["launches_per_day"],
        "launcher": "POSM 0x58daec31 multicall ac9650d8, 1,444 bytes, from %d different EOAs (%s) with high nonces %d-%d, tiny values (%s ETH: the ETH side of a full-range mint), LP fee %s, full-range liquidity (one pool a concentrated range); launches spread over %.1f h (%s). These deployers launch POSM pools at random absurd fees 5%%-99%% (their 132 pools: 60%% x27, 50%% x7, 20%% x7, 25%% x5, 81%% x4, ...); the whole class of POSM launches with fee >= 5%% is 479 pools from 87 deployers in 48 h." % (
            r["n_deployers"], dep, r["nonce_range"][0], r["nonce_range"][1], [v[0] for v in r["values"]], label, r["span_hours"], "first/last block %s" % r["first_last_block"]),
        "first_buy": "any non-launch buy in %d of 5 pools: offset p10/50/90 %s, size %s ETH, to %s, selectors %s, %d distinct wallets (%d EIP-7702 self-calls from==to, i.e. sniper bots buying at +1); real buy (>= 0.0002 ETH) in %d of 5: offsets %s, sizes %s ETH, %d wallets, none the launch wallet, none fresh. The +1 buyers are chain-wide sniper bots (0x36af22df alone swaps 19 times across these deployers' 132 pools; 29 of the 53 first buys in those pools are 0c89e77a self-calls), not the launcher's wallets; the later buys come at random offsets from unrelated aggregator wallets: no operator schedule." % (
            fb["pools_with"], fb["off_p10_50_90"], fb["eth_p10_50_90"], [t[0][:10] for t in fb["to"]], [s[0] for s in fb["sel"]], fb["n_from"], fb["from_eq_to (EIP-7702 self-call)"],
            fr["pools_with"], fr["off_p10_50_90"], fr["eth_p10_50_90"], fr["n_from"]) if fb["pools_with"] else "no buy of any size in any of the 5 pools within 3000 blocks (the only swaps: 2 sells by outside wallets in 0x9101130f, whose launch range sits below the price). Across these 5 deployers' other pools the +1 buyers are chain-wide sniper bots (0c89e77a self-calls, 0x36af22df), not the launcher's wallets: no operator schedule.",
        "pull": "%d of 5 pulled within 3000 blocks (%.0f%%): offset from launch %s; from the first real buy %s; by %s (%d by the launch wallet) via %s. Their 132 pools: %d pulled (%.1f%%), launch offsets p10/50/90 %s." % (
            pu["pulled_3000"], 100 * pu["frac"], pu["off_launch_p10_50_90"], pu["off_from_first_real_buy_p10_50_90"], [b[0][:10] for b in pu["by"]], pu["by_launch_wallet"], [v[0] for v in pu["via"]],
            W234["pull"]["pulled_3000"], 100 * W234["pull"]["frac"], W234["pull"]["off_launch_p10_50_90"]),
        "outsiders": "outsider buys (any non-launch wallet) before the first real buy in %d of 5 pools, sizes %s ETH (snipers); pulled after them %d of %d (delay %s blocks) vs %d of %d without (offset %s). Over the deployers' 132 pools: %d of %d pools with an outsider pulled (delays %s) vs %d of %d without (offsets %s): no faster pull after outsiders, so no trap, but also nothing scheduled to sell into." % (
            tr["pools_with_outsider_before_sched"], tr["outsider_eth_p10_50_90"], tr["pulled_after_outsider"], tr["pools_with_outsider_before_sched"], tr["delay_after_outsider_p10_50_90"],
            tr["pulled_without"], tr["pools_without"], tr["pull_off_without_p10_50_90"],
            W234["trap"]["pulled_after_outsider"], W234["trap"]["pools_with_outsider_before_sched"], W234["trap"]["delay_after_outsider_p10_50_90"],
            W234["trap"]["pulled_without"], W234["trap"]["pools_without"], W234["trap"]["pull_off_without_p10_50_90"]),
        "front_rule": rule(r["front"], "; no real buy by +20 in any pool, every trade sold at +20 into an untouched pool: the loss is the %s LP fee on the way in and out (less than 2 x fee because our own buy dominates these tiny pools). Their 132 pools: %s" % (label, rule(W234["front"]))),
        "follow_rule": rule(r["follow"], ". Their 132 pools: %s" % rule(W234["follow"])),
        "capacity": ("first real buys through %s: not decoded; ASSUMED minOut = 0.99 x launch-state quote -> %s ETH ahead (p10/50/90): the pools hold 4e-5..0.007 ETH, so any stake dwarfs them" % ([s[0] for s in fr["sel"]], r["capacity"]["cap_eth_p10_50_90"])) if r["capacity"]["n"] else "no buy in any pool: nothing to compute",
        "engine_config": "recognizer would be POSM multicall ac9650d8, 1,444 bytes, value < 0.01 ETH, fee %s, tick spacing %s, hooks 0; no fire offset or exit trigger exists (no scheduled buy). The engine's front recognizer (value exactly 2.4333285 ETH, fee 2500, ts 50) already excludes these; any future generic recognizer must reject LP fees above ~1%%." % (label, r["capacity"] and k.split("|")[4]),
        "verdict": "unprofitable", "candidate_score": 0,
        "notes": ("The one pull is not of the launch position: a concentrated range [252500, 255000] added at +1702 to pool 0x2a640c02 and removed at +2009 by 0xa34e2dbc (not the launch wallet); the launch liquidity never moved. " if "250000|2500" in k else "") + "Fee-farm pools: launched at %s LP fee with dust liquidity, bought only by sniper bots that buy every new pool at +1 (0c89e77a self-call wallets, 0x36af22df via 0x1de17737/0x7c8c511c) and by a few aggregator wallets (0x555ce236 via 0x663dc15d c7a76969) at random times. LP fees paid by buyers in 48 h: $%.0f in these deployers' 131 high-fee pools, $%.0f over all 479 POSM fee>=5%% pools (snipers.json). Wider class of 479 pools: front %s." % (
            label, SN["fam2-4 deployers"]["lp_fee_usd"], SN["all POSM fee>=5%"]["lp_fee_usd"], rule(WCL["front"]))})

# controls
fams.append({
    "key": "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true", "known": "vbot-v2.433 (CONTROL)", "count": CV["count"], "launches_per_day": CV["launches_per_day"],
    "launcher": "POSM multicall, value exactly 2.4333285 ETH, a fresh EOA per launch (1843 deployers, nonces 3-11)",
    "first_buy": "bot router 0x1cbaf24d c1120e3d buy (the scheduled buy): offset p10/50/90 %s from launch; generic first real buy (>=0.0002, any router) offset %s, size %s ETH, 0x1cbaf24d in 1317 / decoy router 0x65050a9b in 525 pools" % (C["v2433_sched_off_p10_50_90"], CV["first_buy_real"]["off_p10_50_90"], CV["first_buy_real"]["eth_p10_50_90"]),
    "pull": "%.1f%% pulled within 3000 blocks, offset from launch p10/50/90 %s, from the first real buy %s, all by the launch wallet via 0x1cbaf24d a0f7978d" % (100 * CV["pull"]["frac"], CV["pull"]["off_launch_p10_50_90"], CV["pull"]["off_from_first_real_buy_p10_50_90"]),
    "outsiders": "%d of %d pools have a non-dust outsider (mostly the operator's own decoy wallets 0xb002e8a0/0xf6e55480/0x488faf52, ~0.0001 ETH) before the first real buy; pull delay after it p10/50/90 %s vs %s from launch without" % (CV["trap"]["pools_with_outsider_before_sched"], CV["count"], CV["trap"]["delay_after_outsider_p10_50_90"], CV["trap"]["pull_off_without_p10_50_90"]),
    "front_rule": "scheduled buy = the bot router buy: %s; launched in the live window Oct 10 09:07-11:39 UTC: %s (HANDOFF 16.2 live: +13.97%% mean, +16.25%% median, 405 trades: matches). Generic schedule (first real buy of any router): %s. Pricer vs our 1,080 real relay round trips: model mean %+.3f%% vs real %+.3f%%, median abs diff %.1e, %d of %d within 0.5 pt." % (
        rule(C["v2433_front_bot_sched_all"]), rule(C["v2433_front_livewindow_oct10_0907_1139"]), rule(C["v2433_front_generic_sched"]),
        100 * C["live_relay_calibration"]["model_mean"], 100 * C["live_relay_calibration"]["real_mean"], C["live_relay_calibration"]["abs_diff_median"], C["live_relay_calibration"]["within_0.5pt"], C["live_relay_calibration"]["n"]),
    "follow_rule": rule(CV["follow"]) + " (the follow rule triggers on the bot's own buy and holds into the pull)",
    "capacity": "minOut from calldata word 4: ETH ahead before the bot's buy reverts p10/50/90 %s (minOut/quote %s): the handoff's 0.0122-0.0124" % (C["v2433_capacity_p10_50_90"], C["v2433_minout_over_quote_p10_50_90"]),
    "engine_config": "live today (front)", "verdict": "control-known", "candidate_score": 0,
    "notes": "calibration control: the pricer reproduces the live +14%"})
fams.append({
    "key": "operator-A (launcher 0x3194e326, 77 pools in 67 strict families)", "known": "operator-A (CONTROL)", "count": CA["count"], "launches_per_day": CA["launches_per_day"],
    "launcher": "launcher 0x3194e326 2fcb9108, a fresh launch wallet per pool (nonce 0)",
    "first_buy": "first real buy offset p10/50/90 %s, size %s ETH, Universal Router, %d crowd wallets" % (CA["first_buy_real"]["off_p10_50_90"], CA["first_buy_real"]["eth_p10_50_90"], CA["first_buy_real"]["n_from"]),
    "pull": "%.1f%% pulled within 3000, offset p10/50/90 %s, from the first real buy %s, by the launch wallet via POSM dd46508f" % (100 * CA["pull"]["frac"], CA["pull"]["off_launch_p10_50_90"], CA["pull"]["off_from_first_real_buy_p10_50_90"]),
    "outsiders": "%d of 77 pools with a non-dust outsider before the first real buy; pull delay after it %s vs %s from launch without" % (CA["trap"]["pools_with_outsider_before_sched"], CA["trap"]["delay_after_outsider_p10_50_90"], CA["trap"]["pull_off_without_p10_50_90"]),
    "front_rule": rule(C["opA_front_generic"]) + " (first buy at +24..66, so the +20 deadline comes first)",
    "follow_rule": rule(C["opA_follow"]) + "; trigger offset p10/50/90 %s" % C["opA_follow_trig_p10_50_90"],
    "capacity": "Universal Router (nested): ASSUMED 0.99 x quote -> %s ETH" % CA["capacity"]["cap_eth_p10_50_90"],
    "engine_config": "live today (follow)", "verdict": "control-known", "candidate_score": 0, "notes": "calibration control: follow positive, front negative, as live"})
json.dump({"families": fams}, open(os.path.join(HERE, "results.json"), "w"), indent=1)
print(json.dumps({"families": fams}, indent=1))
