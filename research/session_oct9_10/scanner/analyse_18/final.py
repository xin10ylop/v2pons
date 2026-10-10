"""assemble results.json (the structured output) from stats.json, postwindow.json, devbuy.json, breakeven.json"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "stats.json"))); PW = json.load(open(os.path.join(HERE, "postwindow.json")))
DB = json.load(open(os.path.join(HERE, "devbuy.json"))); BE = json.load(open(os.path.join(HERE, "breakeven.json")))
K = json.load(open(os.path.join(HERE, "keys.json"))); C = S["controls"]
W7 = S["WIDER all 7fde822e launches (imortal.buzz launchpad, every launch contract)"]; WD = S["WIDER deployer 0x06cb3a68 (all its pools)"]
WO = S["WIDER all 0x815542e8 / 7c33638d launches (openlaunch.lol)"]


def fr(s, extra=""):
    if not s or s.get("n", 0) == 0: return "n 0" + extra
    return ("n %d, mean %+.2f%%, median %+.2f%%, win %.0f%%, pulled-first %d, $%+.3f a trade, $%+.2f a day" %
            (s["n"], 100 * s["mean"], 100 * s["median"], 100 * s["win"], s["pulled_first"], s["usd_trade"], s["usd_day"])) + extra


def pw(k):
    ps = [v for v in PW["pools"].values() if v["family"] == k]
    return (min(p["blocks_to_head"] for p in ps), max(p["blocks_to_head"] for p in ps), sum(p["pulls"] for p in ps), sum(p["swaps_after_3000"] for p in ps))


CAL = ("Method check (same code, analyse.py controls): v2.433 front (buy launch+1, sell one block after the bot's first c1120e3d router buy, else +20) "
       "%s on all 1,843 census v2.433 pools and %s on the Oct 10 live window (410 pools; HANDOFF: +13.97%%); our 1,080 real relay trades re-priced at their own "
       "B/S/stake: model mean %+.2f%% vs realised %+.2f%%, all 1,080 within 0.5 pt (median |diff| 3e-16); operator A follow %s; v2.433 capacity from the bot's "
       "real minOut (word 4) %.4f ETH ahead of a 0.05 ETH buy (HANDOFF 6.8: 0.0122-0.0124); gas 2 x 104,000 x the launch block base fee (0.020 gwei) = $%.4f a trade." % (
           fr(C["v2433_front_all"]), fr(C["v2433_front_livewindow"]), 100 * C["live_relay_calibration"]["model_mean"], 100 * C["live_relay_calibration"]["real_mean"],
           fr(C["opA_follow"]), C["v2433_capacity_for_0.05_buys"][1], C["gas_usd_per_trade_v2433_median"]))
IMORTAL = ("The whole imortal.buzz launcher (selector 7fde822e: %d census pools in 48 h = %.0f/day, %d launch contracts of 19,028 bytes, each used for exactly 20 "
           "launches then replaced; 5 deployers, %d pools by 0x06cb3a68) is the same: first buy in %d/%d pools is the dust bot's 2e-6 ETH at +3, a buy >= 0.0002 "
           "ETH in only %d/%d (+3, +843, +959, +1510, +1625; 5 different wallets and routers), and the platform address 0x94dddbb5 (calldata words 7/9) sells ~98%% "
           "of each such buy's ETH back into the pool 2-18 blocks later (5 of 5, delays 2, 3, 12, 13, 18; via 0xfa9b5811 bbb2e1a6 / 0x2fe63b82 c4427054): a back-run, not a pull; "
           "0 pulls within 3,000 blocks in all %d; front %s; follow %s. Break-even: the pools are shallow (virtual ETH depth %.2f ETH), so any buy >= %.4f ETH "
           "behind our 0.0058 would pay, but none is scheduled." % (
               W7["count"], W7["launches_per_day"], W7["n_launch_to"], WD["count"], W7["first_buy_any"]["pools_with"], W7["count"], W7["first_buy_real"]["pools_with"],
               W7["count"], W7["count"], fr(W7["front"]), fr(W7["follow"]), BE["imortal 7fde822e (fee 1%, tick0 201800)"]["eth_depth_L_over_s"],
               BE["imortal 7fde822e (fee 1%, tick0 201800)"]["breakeven_buy_eth"]))
fam = []
meta = {K[0]: ("0x80521fc9", "8ac5f6b2", "2006-2022", "Oct 09 07:47-11:01 UTC", "6/6 at +3"),
        K[2]: ("0xcd1e2cbe", "5c798ed7", "1991-2003", "Oct 09 06:37-07:37 UTC", "+2 in 1, +3 in 5"),
        K[3]: ("0xd912ed6c", "27f33e28", "2026-2044", "Oct 09 11:17-12:46 UTC", "+2 in 2, +3 in 4")}
for k in K:
    s = S[k]; h0, h1, npull, nlate = pw(k)
    if k != K[1]:
        c, ch, nn, when, offs = meta[k]
        late = (" (one pool: a 2.24e-5 ETH buy at +3315 and its sell at +3595, one wallet)" if nlate else "")
        fam.append({
            "key": k, "known": "none", "count": s["count"], "launches_per_day": s["launches_per_day"],
            "launcher": ("imortal.buzz user-token launchpad: deployer 0x06cb3a68 (one wallet, nonces %s) calls its launch contract %s (19,028 bytes, code hash %s, "
                         "used for exactly 20 launches: 6 at 772 bytes, the rest 740/804/836 = other metadata lengths) with 7fde822e, value 0, gas ~1.7M, priority 0; "
                         "calldata = token name/symbol, an imortal.buzz IPFS URI, an x.com link, platform address 0x94dddbb5 (words 7, 9), 2500 (word 8), 1.7e18 (word 10). "
                         "The contract itself mints a single-sided token range [132800, 201800], L 3.2156e22 at tick 201800 (no ETH, no buy in the launch tx). "
                         "6 launches %s (3.0/day as a 48-h average; the deployer as a whole: %d pools, %.0f/day)") % (nn, c, ch, when, WD["count"], WD["launches_per_day"]),
            "first_buy": ("first non-launch buy in 6/6 pools: the chain-wide dust bot 0xe71a69f4 (one recurring wallet, not fresh; it buys every new pool on the chain) via "
                          "the Universal Router execute, offset %s (p10/50/90 %s), size 2e-6 ETH (p10/50/90 %s); no buy >= 0.0002 ETH in any pool within 3,000 blocks "
                          "(0/6) or to the head%s; fraction of pools with an operator-scheduled buy: 0") % (offs, "/".join("+%d" % x for x in s["first_buy_any"]["off_p10_50_90"]),
                                                                                                             "/".join("%g" % x for x in s["first_buy_any"]["eth_p10_50_90"]), late),
            "pull": ("0/6 pulled within 3,000 blocks; 0/6 ever (eth_getLogs of every Swap/ModifyLiquidity of these pools to head %d, %d-%d blocks after launch: %d pulls); "
                     "offsets from launch and from the first buy n/a; nobody pulls (0 of the deployer's %d pools within 3,000 blocks)") % (PW["head"], h0, h1, npull, WD["count"]),
            "outsiders": ("6/6 pools have an outside buy before any scheduled buy (the dust bot's 2e-6 ETH at +2/+3; there is no scheduled buy); pulled after it 0/6, "
                          "pools without an outsider 0: no pull exists to time, so the trap test has nothing to compare (the 454-pool deployer: 0 pulls; its 5 real "
                          "outside buys were each answered by the platform 0x94dddbb5 selling ~98% back within 2-18 blocks, not by a pull)"),
            "front_rule": fr(s["front"], " (3.0/day). No scheduled buy by +20 in 0/6 pools, so every sell lands at launch+20 into an untouched pool: two 1%% pool fees "
                                         "+ gas (gross %.2f%%); held to +3,000 it is %+.2f%%" % (100 * s["front_gross_p10_50_90"][1], 100 * s["front_hold3000"]["mean"])),
            "follow_rule": "n 0: no pool ever had a buy >= 0.0002 ETH (no trigger), $0 a trade, $0 a day",
            "capacity": "n/a: no scheduled buy exists (no router calldata to decode, nothing to assume a minOut on)",
            "engine_config": ("nothing to trade. For the record: recognizer = tx from 0x06cb3a68 (or selector 7fde822e to any of its rotating 19,028-byte contracts), "
                              "value 0, calldata 740-836 bytes; eligibility fee 10000, ts 200, hooks 0, L 3.2156e22; no exit trigger exists (no operator buy, no router), "
                              "so no fire offset or hold makes money"),
            "verdict": "no-schedule", "candidate_score": 0,
            "notes": ("A user-token launchpad, not a pump-and-pull operator: no operator buy, no decoys, no crowd, liquidity never removed, nobody but the dust bot "
                      "touches the pools. The strict family is one launch contract's 6 launches of 772-byte metadata; families %s, %s and %s are the same launcher in "
                      "three consecutive hours. ") % (K[2][:10], K[0][:10], K[3][:10]) + IMORTAL + " " + CAL})
    else:
        a = DB["openlaunch all H100"] if "openlaunch all H100" in DB else None
        fam.append({
            "key": k, "known": "none", "count": s["count"], "launches_per_day": s["launches_per_day"],
            "launcher": ("openlaunch.lol user-token launchpad: contract 0x815542e8 (13,681 bytes, code hash 670175c9), selector 7c33638d, value 0, gas ~1.8M, priority 0; "
                         "calldata 833 bytes = token name/symbol (e.g. 'BOT LAUNCH'/'BL'), an openlaunch.lol/api/launch/meta/<deployer>/<hash> URI, 0xdead, 1000, the "
                         "deployer's own address, 9000; the liquidity is minted through the POSM, single-sided token range [-887200, 184000] (L 1.0109e23, 4 pools) or "
                         "[-887200, 193200] (L 6.38e22, 2 pools). 3 different deployers, 2 launches each (0x14a202fb nonces 74/75, 0xbabb7be0 272/275, 0x61ae738f 8/14), "
                         "Oct 09 13:41 - Oct 10 08:35 UTC; the launcher as a whole: %d pools in 48 h (%.1f/day), %d deployers, fees 1%% and 3%%") % (
                             WO["count"], WO["launches_per_day"], WO["n_deployers"]),
            "first_buy": ("a buy in 1/6 pools only: the launch wallet 0x61ae738f itself, 1e-6 ETH at +1902 and again at +2155 via the Universal Router (a test buy); "
                          "no buy >= 0.0002 ETH in any pool (0/6), no dust-bot buy, nothing from any other wallet, to the head; fraction with a scheduled buy: 0. "
                          "Across the whole openlaunch launcher (35 pools) a buy >= 0.0002 ETH came in 4/35, each the launch wallet's own dev buy (+45/+57/+67/+78, "
                          "0.005-0.03 ETH, Universal Router, 4 different wallets), followed 7-9 blocks later by two sniper wallets (0x13301ff0, 0xd54bad00) that sell "
                          "~290 blocks later"),
            "pull": ("0/6 pulled within 3,000 blocks; 0/6 ever (logs to head %d, %d-%d blocks after launch); offsets n/a; nobody pulls (0 of the launcher's 35 pools "
                     "within 3,000 blocks)") % (PW["head"], h0, h1),
            "outsiders": ("0/6 pools have an outside buy (no wallet but the launch wallet's 1e-6 ETH test buys ever touched them); no pull in any pool, so the trap "
                          "test has nothing to compare (launcher-wide: outsiders in 10/35, pulls 0/35)"),
            "front_rule": fr(s["front"], " (3.0/day). No scheduled buy by +20 (0/6): sold at launch+20 into an untouched pool, two 3%% fees + gas (gross %.2f%%); "
                                         "held to +3,000 %+.2f%%. Waiting for the launcher's dev buy (wider 35 pools, sell one block after it, else +100): %s; the 4 dev-buy "
                                         "pools return -1.96%%, -5.13%%, -0.63%%, -0.63%%: the pools are deep (virtual ETH depth 4.1-10.2 ETH; break-even buy behind us 0.13-0.33 ETH)" % (
                                             100 * s["front_gross_p10_50_90"][1], 100 * s["front_hold3000"]["mean"], fr(DB["openlaunch all H100"]))),
            "follow_rule": ("n 0: no buy >= 0.0002 ETH in any of the 6 pools, $0 a trade, $0 a day (the whole launcher, 4 dev-buy triggers: %s)" % fr(WO["follow"])),
            "capacity": "n/a: no scheduled buy exists in this family (the launcher's 4 dev buys go through the Universal Router's nested execute: minOut not decoded; at an ASSUMED minOut = 0.99 x launch quote they would leave 0.021-0.051 ETH of room, irrelevant at a loss)",
            "engine_config": ("nothing to trade. For the record: recognizer = tx to 0x815542e8, selector 7c33638d, value 0, calldata 740-964 bytes; eligibility fee 30000 "
                              "(or 10000), ts 200, hooks 0; no exit trigger (no operator buy, no router)"),
            "verdict": "no-schedule", "candidate_score": 0,
            "notes": ("A second user-token launchpad (openlaunch.lol): each launch is a different user's token, minted single-sided at a 3% fee, then left alone; "
                      "no operator buy, no decoy, no pull, no dust bot in this family. Not related to the imortal.buzz families. " + CAL)})
json.dump({"families": fam, "controls": C}, open(os.path.join(HERE, "results.json"), "w"), indent=1)
for f in fam:
    print(f["key"]); print("  front", f["front_rule"][:200]); print("  follow", f["follow_rule"][:150])
print(CAL)
