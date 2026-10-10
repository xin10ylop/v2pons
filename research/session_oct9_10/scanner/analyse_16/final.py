"""assemble results.json (the structured output) from stats.json, calib.json, controls.json and postwindow.json"""
import json
OUT = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/analyse_16"
S = json.load(open(OUT + "/stats.json")); C = json.load(open(OUT + "/calib.json")); CT = json.load(open(OUT + "/controls.json")); PW = json.load(open(OUT + "/postwindow.json"))
K = json.load(open(OUT + "/keys.json"))
W7 = S["WIDER all 7fde822e launches (every launch contract)"]; WF = S["WIDER all ff734f50 launches (3 launch contracts)"]


def fr(s, extra=""):
    if not s or s.get("n", 0) == 0: return "n 0" + extra
    return ("n %d, mean %+.2f%%, median %+.2f%%, win %.0f%%, pulled-first %d, $%+.3f a trade, $%+.2f a day" %
            (s["n"], 100 * s["mean"], 100 * s["median"], 100 * s["win"], s["pulled_first"], s["usd_trade"], s["usd_day"])) + extra


CAL = ("Pricer calibrated first (calib.py, same code): v2.433 front (buy launch+1, sell one block after the bot's first router buy) %s on the live window "
       "(Oct 10 ~09:05-11:40 UTC) and %s on all 1,843 census v2.433 pools; the 399 live front trades of Oct 10 re-priced at their own stake/buy/sell "
       "blocks: model mean %+.2f%% vs live %+.2f%% (median diff %+.3f%%, max |diff| %.2f%%, gas); operator A follow %s; v2.433 capacity from the bot's "
       "real minOut %.4f ETH ahead of a 0.05 ETH buy (HANDOFF 6.8: 0.0122-0.0124)." % (
           fr(C["v2433_front_livewindow"]), fr(C["v2433_front_all"]), 100 * C["live_audit"]["model_mean"], 100 * C["live_audit"]["live_mean"],
           100 * C["live_audit"]["diff_median"], 100 * C["live_audit"]["max_abs_diff"], fr(C["opA_follow"]), C["v2433_capacity_for_0.05_buy"][1]))
WIDE7 = ("The whole 7fde822e launcher (all %d census pools on 27 launch contracts, 5 deployers, %d by 0x06cb3a68; %.0f/day) is the same: first buy "
         "in 490/490 is the dust bot's 2e-6 ETH at +3, a real buy (>= 0.0002) in only %d/490 (+3, +843, +959, +1510, +1625; 5 different wallets and routers), "
         "0 pulled; front %s; follow %s." % (W7["count"], 454, W7["launches_per_day"], W7["first_buy_real"]["pools_with"], fr(W7["front"]), fr(W7["follow"])))
fam = []
# ---- family 1 and 2: 0xe43be69c, the same contract and deployer split by calldata length (metadata string length)
for k, extra_fb, extra_fo, extra_cap, launches in [
    (K[0], "; first buy >= 0.0002 ETH: 1/7 pools (0.00235 ETH at +1625 by 0xf42b73d2 via 0xb92fe925 cd6e13f7, an outsider; 13 blocks later 0x94dddbb5, the platform address written into every launch's calldata, sold 0.0023 ETH of the token)",
     " (the one +1625 outsider buy: our buy +1626, no next buy, sold +1630); 0 trades in the other 6 pools",
     "n/a: no scheduled buy exists. The single outside 0.00235 ETH buy (via 0xb92fe925 cd6e13f7, calldata not decoded) would allow 0.0068 ETH ahead at an ASSUMED minOut = 0.99 x its launch-state quote; it is not scheduled.",
     "Oct 10 02:17-03:51 UTC"),
    (K[1], "; first buy >= 0.0002 ETH: 0/7 pools", "; no pool ever had a buy >= 0.0002 ETH", "n/a: no scheduled buy in any pool", "Oct 10 02:26-03:41 UTC")]:
    s = S[k]
    fam.append({
        "key": k, "known": "none", "count": s["count"], "launches_per_day": s["launches_per_day"],
        "launcher": ("contract 0xe43be69c (19,028 bytes, code hash 4eaf3ea3) called with 7fde822e, value 0, calldata %s bytes = token name/symbol, an imortal.buzz IPFS "
                     "metadata URI and x.com links (a user-token launchpad); calldata words 7 and 9 = 0x94dddbb5 (platform address), word 8 = 2500, word 10 = 1.7e18 "
                     "(1.7 ETH starting cap); one deployer 0x06cb3a68 (nonces %s; it launched 454 of the census's 490 7fde822e pools over 27 contracts), gas ~1.7M, "
                     "priority 0; single-sided token range [132800, 201800], L 3.2156e22 at tick 201800, no ETH and no buy in the launch tx. %d launches in %s "
                     "(%.1f/day over the 48 h census)") % (k.split("|")[2], "%d-%d" % (min(s["nonces"]), max(s["nonces"])), s["count"], launches, s["launches_per_day"]),
        "first_buy": ("first non-launch buy in %d/%d pools: the chain-wide dust bot 0xe71a69f4 (one wallet, not fresh, buys every new pool on the chain) via the Universal "
                      "Router execute, offset p10/50/90 %s blocks, size 2e-6/2e-6/2e-6 ETH%s. Fraction of pools with an operator-scheduled buy: 0") % (
                          s["first_buy_any"]["pools_with"], s["count"], "/".join("+%g" % x for x in s["first_buy_any"]["off_p10_50_90"]), extra_fb),
        "pull": ("0/%d pulled within 3,000 blocks, 0/%d ever (eth_getLogs of every Swap/ModifyLiquidity of these pools to head %d, 575k-630k blocks after launch: only the "
                 "launch mint and the swaps above); offsets n/a; nobody pulls (0 of the deployer's 454 pools within 3,000 blocks)") % (s["count"], s["count"], PW["head"]),
        "outsiders": ("%d/%d pools got an outside buy >= 0.0002 ETH (none before any scheduled buy, as there is none); pulled after it 0, pulled without one 0/%d: the trap "
                      "test has nothing to compare (no pull at all, in this family or in the 490-pool launcher)") % (
                          s["trap"]["pools_with_outsider_real_buy"], s["count"], s["trap"]["pools_without"]),
        "front_rule": fr(s["front"], " (%.1f/day). No scheduled buy by +20 in 0/%d pools: every sell lands at launch+20 into an untouched pool, so the trade is two 1%% pool "
                                     "fees + 0.07%% gas (gross %.2f%%); held to +3,000 it is %s" % (s["launches_per_day"], s["count"], 100 * s["front_ret_gross_p10_50_90"][1],
                                                                                                  "%+.2f%%" % (100 * s["front_hold3000"]["mean"]))),
        "follow_rule": fr(s["follow"], extra_fo),
        "capacity": extra_cap,
        "engine_config": ("nothing to trade. For the record: recognizer = tx to 0xe43be69c (or any of the 27 7fde822e launch contracts), selector 7fde822e, value 0, calldata "
                          "644-964 bytes; eligibility fee 10000, ts 200, hooks 0; no exit trigger exists (no operator buy, no router), so no fire offset/hold makes money"),
        "verdict": "no-schedule", "candidate_score": 0,
        "notes": ("A user-token launchpad (imortal.buzz), not a pump-and-pull operator: no operator buy, no decoys, no crowd, liquidity never removed, nobody but the dust "
                  "bot touches the pools. Families %s and %s are one launcher split by metadata length (same contract, deployer, hours). " % (K[0][:12] + "|772", K[1][:12] + "|804")) + WIDE7 + " " + CAL})
# ---- family 3: 0x1756c648
s = S[K[2]]
fam.append({
    "key": K[2], "known": "none", "count": s["count"], "launches_per_day": s["launches_per_day"],
    "launcher": ("contract 0x1756c648 (19,028 bytes, code hash 04dc74ae: the same 7fde822e launchpad code family, another instance) called with 7fde822e, value 0, calldata "
                 "740 bytes (name/symbol + imortal.buzz metadata URI, no social links; 'Paxos' x5, 'GLORP'); calldata words 7/9 = 0x94dddbb5, word 10 = 1.7e18 as in the 0xe43be69c "
                 "launches; one fresh deployer 0x17ad4d45 (nonces 7-12; its whole census life is 12 launches, nonces 1-12, all on this contract, within 1.04 h), gas 1.66M, "
                 "priority 0; single-sided range [132800, 201800], L 3.2156e22; 6 launches Oct 8 19:14-19:40 UTC (3.0/day over the census)"),
    "first_buy": ("first non-launch buy in 6/6 pools: the dust bot 0xe71a69f4 via the Universal Router, offset p10/50/90 +2/+3/+4, 2e-6 ETH; one wallet; first buy >= 0.0002 ETH: "
                  "0/6 within 3,000 blocks (after the window: one pool, 0xd52189f1, got a 0.000457 ETH buy at +3435 and a 0.000447 ETH sell at +3437). Scheduled buy: none"),
    "pull": "0/6 within 3,000 blocks and 0/6 ever (eth_getLogs to head %d, ~1.7M blocks after launch: only the launch mint); nobody pulls" % PW["head"],
    "outsiders": "0/6 pools with an outside buy >= 0.0002 ETH within 3,000 blocks; 0 pulls at all, so the trap test is empty",
    "front_rule": fr(s["front"], " (3.0/day). No buy by +20: every sell at launch+20 into an untouched pool = two 1%% fees + gas; held to +3,000 the same (%+.2f%%)" % (100 * s["front_hold3000"]["mean"])),
    "follow_rule": "n 0: no pool ever had a buy >= 0.0002 ETH within 3,000 blocks",
    "capacity": "n/a: no scheduled buy",
    "engine_config": "nothing to trade (recognizer would be to 0x1756c648 / any 7fde822e launch contract, selector 7fde822e, value 0; fee 10000 ts 200 hooks 0; no exit trigger exists)",
    "verdict": "no-schedule", "candidate_score": 0,
    "notes": "Same imortal.buzz launchpad as the 0xe43be69c families, another contract instance and a short-lived deployer. " + WIDE7 + " " + CAL})
# ---- family 4: 0x1f3af76c ff734f50
s = S[K[3]]
fam.append({
    "key": K[3], "known": "none", "count": s["count"], "launches_per_day": s["launches_per_day"],
    "launcher": ("contract 0x1f3af76c (22,031 bytes, code hash 68994779) called with ff734f50, calldata 1,060 bytes (name/symbol, supply 1e9 x 1e18, fee 3000, ts 60, a dev-buy "
                 "amount = the tx value); 4 different deployers (0x962889c5 x2 nonces 38/41, 0xd000543b x2 nonces 16/19, 0x60087941 nonce 14, 0x7afcdba7 nonce 0), value "
                 "0 / 0.0001 / 0.0002 / 0.0004 ETH = an optional dev buy executed inside the launch tx (3 of 6), gas 2.2-5.9M, priority 1 wei; three liquidity ranges per launch "
                 "(token only, tick0 191160 / 198060 / 207240); tokens 'Smoke1', 'AQUA', 'BRIO', 'GALE', 'KITE', 'Bot E2E': launchpad smoke/end-to-end test launches. "
                 "6 launches Oct 9 15:12-15:53 UTC (3.0/day over the census); the ff734f50 selector has 10 pools in all on 3 contracts (5/day)"),
    "first_buy": ("first non-launch buy in 5/6 pools: the dust bot 0xe71a69f4 (2e-6 ETH at +3, 3 pools) and 0xe3ba8a08 (2e-5 ETH at +63/+65, 2 pools), both via the Universal "
                  "Router; p10/50/90 offset +3/+3/+65, size 2e-6/2e-6/2e-5 ETH; first buy >= 0.0002 ETH: 0/6 within 3,000 blocks (the only later buy is the launch wallet "
                  "0x7afcdba7 itself, 0.0001 ETH at +669 through 0x6131b5fa e21fd0e9). The dev buys are inside the launch tx (0.0001-0.0004 ETH, 3 pools). Scheduled buy: none"),
    "pull": ("0/6 within 3,000 blocks and 0/6 ever (eth_getLogs to head %d, ~1.0M blocks after launch); after the window the pools get 82 tiny buys/sells "
             "(2e-5..4e-5 ETH every ~100-150 blocks from a keeper/test wallet) and 2-4 more liquidity ADDS each, never a removal") % PW["head"],
    "outsiders": "0/6 pools with an outside buy >= 0.0002 ETH within 3,000 blocks (2 got 2e-5 ETH specks); 0 pulls, so the trap test is empty",
    "front_rule": fr(s["front"], " (3.0/day). No buy by +20 in 0/6: every sell at launch+20 = two 0.3%% fees + gas (gross %.2f%%); held to +3,000: %+.2f%%. Wider ff734f50 (10 pools): %s" % (
        100 * s["front_ret_gross_p10_50_90"][1], 100 * s["front_hold3000"]["mean"], fr(WF["front"]))),
    "follow_rule": "n 0 (no buy >= 0.0002 ETH after the launch tx within 3,000 blocks). Wider ff734f50 (10 pools on 3 contracts): " + fr(WF["follow"]) + " (triggers +295/+637/+857, 2 of 3 by the launch wallet itself; no next buy within 4 blocks)",
    "capacity": "n/a: no scheduled buy (wider ff734f50: the 3 late real buys at an ASSUMED 0.99 x launch quote allow 5e-6 to 0.0033 ETH ahead; not scheduled)",
    "engine_config": "nothing to trade (recognizer would be to 0x1f3af76c, selector ff734f50, calldata 1,060, any value; fee 3000 ts 60 hooks 0; no exit trigger exists)",
    "verdict": "no-schedule", "candidate_score": 0,
    "notes": ("A small multi-deployer launchpad contract being tested ('Smoke1', 'Bot E2E'): dev buy inside the launch, three-range token-only liquidity, no operator buy afterwards, "
              "no pull ever, near-zero outside flow (0.000846 ETH of buys in all 6 pools in 3,000 blocks). The 0.3% fee makes the no-buy front cost only -0.67%, but there is "
              "nothing to sell into. " + CAL)})
# ---- controls
cv = CT["vbot-v2.433"]; ca = CT["operator-A"]
fam.append({
    "key": "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true (value 2.4333285)", "known": "vbot-v2.433 (CONTROL)", "count": cv["count"],
    "launches_per_day": cv["per_day"],
    "launcher": "POSM multicall ac9650d8, 1,444 bytes, value exactly 2.4333285 ETH, fresh wallet per launch",
    "first_buy": "scheduled buy = the bot router 0x1cbaf24d c1120e3d in %d/%d pools, offset p10/50/90 %s, size %s ETH, %d distinct sender wallets" % (
        cv["with_sched"], cv["count"], cv["sb_off_p10_50_90"], cv["sb_eth_p10_50_90"], cv["sb_from_distinct"]),
    "pull": "%d/%d pulled within 3,000 blocks, offset from launch p10/50/90 %s, from the bot buy %s, all by the launch wallet through the bot router" % (
        cv["pulled_3000"], cv["count"], cv["pull_off_p10_50_90"], cv["pull_from_sb_p10_50_90"]),
    "outsiders": "pools with a buy >= 0.0002 ETH ahead of the bot's buy (decoys counted): %d; pull delay after the bot buy with them %s vs without %s" % (
        cv["pools_with_real_buy_ahead_of_sched"], cv["trap"]["pull_from_sb_with"], cv["trap"]["pull_from_sb_without"]),
    "front_rule": "live window " + fr(C["v2433_front_livewindow"]) + "; all census pools " + fr(C["v2433_front_all"]) + "; live trades re-priced: model %+.2f%% vs live %+.2f%% on %d" % (
        100 * C["live_audit"]["model_mean"], 100 * C["live_audit"]["live_mean"], C["live_audit"]["n"]),
    "follow_rule": "not the family's trade",
    "capacity": "from the bot's real minOut (calldata word 4 = 0.99 x launch quote): p10/50/90 %s ETH ahead; 0.05 ETH buys %.4f" % (
        [round(x, 4) for x in cv["cap_p10_50_90"]], C["v2433_capacity_for_0.05_buy"][1]),
    "engine_config": "the live front engine", "verdict": "control-known", "candidate_score": 0,
    "notes": "calibration control: the pricer reproduces +14% and the live trades within 0.2%"})
fam.append({
    "key": "operator A (launch to 0x3194e326 / selector 2fcb9108)", "known": "operator-A (CONTROL)", "count": ca["count"], "launches_per_day": ca["per_day"],
    "launcher": "operator A launcher 0x3194e326",
    "first_buy": "first buy >= 0.0002 ETH in %d/%d, offset p10/50/90 %s, size %s ETH, via %s, %d distinct wallets" % (
        ca["with_sched"], ca["count"], ca["sb_off_p10_50_90"], ca["sb_eth_p10_50_90"], ca["sb_to"][0][0], ca["sb_from_distinct"]),
    "pull": "%d/%d within 3,000, offset p10/50/90 %s from launch, %s from the first real buy, by the launch wallet through the POSM" % (
        ca["pulled_3000"], ca["count"], ca["pull_off_p10_50_90"], ca["pull_from_sb_p10_50_90"]),
    "outsiders": "none ahead of the first real buy in the census", "front_rule": fr(C["opA_front_generic"]),
    "follow_rule": fr(C["opA_follow"]), "capacity": "assumed 0.99 x quote: p10/50/90 %s ETH" % ([round(x, 4) for x in ca["cap_p10_50_90"]]),
    "engine_config": "the live follow engine", "verdict": "control-known", "candidate_score": 0, "notes": "calibration control (HANDOFF: about +2-4% a trade)"})
json.dump({"families": fam}, open(OUT + "/results.json", "w"), indent=1)
for f in fam: print(json.dumps(f)[:600]); print()
