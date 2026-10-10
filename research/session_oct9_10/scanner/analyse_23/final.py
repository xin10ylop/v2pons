"""Build the structured output (families_out.json) from results.json (analyse.py) and hookfee.json."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "results.json"))); K = json.load(open(os.path.join(HERE, "keys.json")))
g = lambda i: R["F%d %s" % (i + 1, K[i])]
W1 = R["F1F2-WIDE the high-fee POSM 2020-byte class (launch to POSM, ac9650d8, 2020 bytes, fee >= 10%)"]
D1 = R["F1-DEPLOYERS all launches of F1's 4 deployers"]; D2 = R["F2-DEPLOYER all launches of 0xa5f090eb"]
D3 = R["F3-DEPLOYERS all launches of 0xc6641814 / 0x692f74bc"]; L4 = R["F4-LAUNCHER all launches through 0x78ba8b21"]
W4 = R["F4-WIDE the loose 7fde822e class (27 launch contracts, 454 of 490 by 0x06cb3a68)"]
CV = R["CONTROL vbot-v2.433"]; CA = R["CONTROL operator-A"]; C = R["controls"]


def rule(s, extra=""):
    if not s.get("n"): return "n 0" + extra
    return ("n %d, mean %+.2f%%, median %+.2f%%, win %.0f%%, pulled-first %d, $%+.3f a trade, $%+.2f a day (%.1f trades/day)%s"
            % (s["n"], 100 * s["mean"], 100 * s["median"], 100 * s["win"], s["pulled_first"], s["usd_trade"], s["usd_day"], s["trades_day"], extra))


fam = []
f = g(0)
fam.append({
    "key": K[0], "known": "none", "count": f["count"], "launches_per_day": f["launches_per_day"],
    "launcher": "POSM 0x58daec31 multicall ac9650d8, 2,020 bytes = initializePool (f7020405) + a signed Permit2 permit (002a3e3a) + modifyLiquidities (dd46508f: MINT_POSITION, SETTLE_PAIR, SWEEP): the Uniswap interface's create-pool-and-add layout, not a bot's call. Full range -880000..880000, LP fee 80%, dust liquidity: tx values 0.000095-0.000358 ETH, 5 distinct. 4 deployers (0x3541bae6 x2, 0xe620839e, 0x42fdb641, 0x45fcadcb), nonces 5-7412, spread Oct 8 22:15 to Oct 9 18:38 UTC. These are long-lived wallets that launch high-fee pools at random fees: all 33 of their launches are POSM 2020/1444-byte calls at fees of 40-91%.",
    "first_buy": "No buy of 0.0002 ETH or more in any of the 5 pools within 3,000 blocks (0/5). The only buy of any size is one 1.75e-6 ETH dust buy at +115 (wallet 0x43745495 via 0xf69cd0fe, 69508f86; that wallet dust-buys other high-fee pools too). Also 3 sells (+1, +99, +99) that pull 0.0004 ETH of the dust liquidity out: EIP-7702 self-calling wallets 0xbab546d9 and 0x2c859797 (0c89e77a), and 0x698df2d4 via 0x796a6274. There is no router and no sender pattern to follow.",
    "pull": "0 of 5 pulled within 3,000 blocks; none of the 4 deployers' 33 launches was pulled before +491 (3 pulled at +491/+1573/+2632 through POSM dd46508f by the launch wallet).",
    "outsiders": "1 pool had a 1.75e-6 ETH dust buy and no pool had a scheduled buy. With no pull at all, the trap test has nothing to compare: with an outsider 0/1 pulled, without 0/4.",
    "front_rule": rule(f["front"], ". All 5 sold at launch+20 with no scheduled buy: -80.7%..-89.8% each. The 80% LP fee is paid on both legs, and the 0.0058 ETH stake is 16-61x the ETH in the pool (launch values 0.000095-0.000358). With no 20-block cap (deadline +3000) it is the same, mean -88.28%."),
    "follow_rule": "n 0: no buy of >= 0.0002 ETH, so no trigger.",
    "capacity": "n/a: there is no scheduled buy to sit ahead of.",
    "engine_config": "Not worth trading. If it were armed: launch = to 0x58daec31, ac9650d8, 2,020 bytes, any value. The eligibility filter must reject it: LP fee 800000 ppm. The engine should refuse any pool whose LP fee is above about 1%.",
    "verdict": "no-schedule", "candidate_score": 0,
    "notes": ("Wider class (launch to POSM, ac9650d8, 2,020 bytes, fee >= 10%%): %d pools by %d deployers (%.0f a day), %d buys in all, %.3f ETH in over 48 h. %d pools had any buy >= 0.0002 ETH (at +1..+1580, 5 different wallets through 5 different routers), %d were pulled (+437..+2417, all by the launch wallet through POSM). Front on the class: %s; follow: %s. It is a fee trap, not a schedule: the 20-99%% LP fee goes to the deployer's position, and the few sniper bots that buy in (0x5399d94d 814920c0, 0x6e2a35a7 0c307f76, ...) lose most of their input. Pricer: analyse_23/common23.py (analyse_22's replay, calibrated: v2.433 median +14.01%%, live window +13.95%%)."
              % (W1["count"], W1["n_deployers"], W1["launches_per_day"], W1["swaps_non_launch"]["buys"], W1["swaps_non_launch"]["eth_in"], W1["first_buy_real"]["pools_with"], W1["pull"]["pulled_3000"], rule(W1["front"]), rule(W1["follow"])))})
f = g(1)
fam.append({
    "key": K[1], "known": "none", "count": f["count"], "launches_per_day": f["launches_per_day"],
    "launcher": "POSM multicall ac9650d8, 2,020 bytes (the same create+permit+mint layout as F1), LP fee 87%, full range -878700..878700, tx values 0.000024-0.000393 ETH. One deployer, 0xa5f090eb (nonces 2003-2048), launched all 5 within 54 minutes (Oct 10 02:09-03:04 UTC). Its 9 launches in the window are all at fees of 34-87%.",
    "first_buy": "None: not one swap of any size in any of the 5 pools within 3,000 blocks. Across all 9 of the deployer's launches: 1 buy (6.7e-5 ETH at +1 by an EIP-7702 self-call 0x7a93c59e) and 1 sell.",
    "pull": "0 of 5 pulled within 3,000 blocks (0 of 9 across the deployer's launches).",
    "outsiders": "None. No buys and no pulls, so the trap test is empty.",
    "front_rule": rule(f["front"], ". All sold at launch+20 into an untouched pool: -89.3%%..-96.1%% each, from the 87%% fee on both legs (the deployer's 9 launches: %s)." % rule(D2["front"])),
    "follow_rule": "n 0: no buy at all.",
    "capacity": "n/a: no scheduled buy.",
    "engine_config": "Not worth trading. Recognizer: to 0x58daec31, ac9650d8, 2,020 bytes, from 0xa5f090eb. The eligibility filter must reject it: LP fee 870000 ppm.",
    "verdict": "no-schedule", "candidate_score": 0,
    "notes": "Part of the same high-fee POSM 2020-byte class as F1 (168 pools, 63 deployers, 0.041 ETH bought in 48 h, front mean -75%). It is a dead, fee-trap pool class with no operator buying its own pools."})
f = g(2)
hf = json.load(open(os.path.join(HERE, "hookfee.json")))
fam.append({
    "key": K[2], "known": "none", "count": f["count"], "launches_per_day": f["launches_per_day"],
    "launcher": "Launcher contract 0x6d9ba28f (14,899 bytes), aa7ec999, 580 bytes, ~908k gas. It creates the token and the pool (hook 0xd7d01126, 10,081 bytes; PoolKey fee 0; tick spacing 200; single-sided token range -887200..200000 at tick 200000; L 4.54e22 every time) and makes a dev buy in the launch tx with the whole tx value (2.2e-6 to 0.000225 ETH; 99% reaches the pool). The hook keeps 1%: its 0xe0e765ab event carries exactly 1% of the ETH in, in 8 of 8 receipts. 2 deployers: 0xc6641814 (3 launches, nonces 0-12) and 0x692f74bc (2, nonces 4-6), Oct 9 01:46 to Oct 10 05:25 UTC. Nothing else on the chain used this launcher or hook in the 48 h.",
    "first_buy": "No buy >= 0.0002 ETH outside the launch tx in any pool (0/5). The first non-launch buy came in 3 of 5 pools, at +592/+724/+867 and 2.2e-6 to 3.95e-5 ETH: 2 by wallet 0xd2afc6fe via router 0x65050a9b (4d819a2a, the router of the volume bot's decoys; it bought exactly the dev buy's amount, with 1% router + 1% hook taken) and 1 by the deployer 0x692f74bc itself via 0x294df973. The deployers' 2 other launches (POSM-style 0x0000ffff, fee 0.25%) had 1 buy >= 0.0002: 0.000201 ETH by the deployer at +889.",
    "pull": "0 of 5 pulled within 3,000 blocks (0 of 7 across both deployers).",
    "outsiders": "2 pools had dust buys from 0xd2afc6fe (2.2e-6 and 1.1e-5 ETH) before any scheduled buy, which never came. No pull with or without them (0/2 vs 0/3), so the trap test cannot be run.",
    "front_rule": rule(f["front"], ". All sold at launch+20 into an unchanged pool: the cost is the hook's 1% ETH tax each way (buy side measured; sell side ASSUMED 1%, no sell was ever seen) plus gas of $0.011."),
    "follow_rule": "n 0: no buy of >= 0.0002 ETH after the launch tx.",
    "capacity": "n/a: no scheduled buy. The only later buys are 1e-5 ETH specks.",
    "engine_config": "Not worth trading. Recognizer: to 0x6d9ba28f, aa7ec999, 580 bytes, value = dev buy; hook 0xd7d01126 (1% ETH tax).",
    "verdict": "no-schedule", "candidate_score": 0,
    "notes": "A tiny hand-run hook launchpad: 5 launches in 28 h with dev buys of $0.005-$0.58 and nobody trading after. The pricer applies the hook's tax as an ETH-side cut (common23.HOOK_ETH_TAX). Receipts are in analyse_23/hookfee_rcpts.json (8 receipts plus 4 eth_getCode calls)."})
f = g(3)
fam.append({
    "key": K[3], "known": "none", "count": f["count"], "launches_per_day": f["launches_per_day"],
    "launcher": "Launch contract 0x78ba8b21 (19,036 bytes), 7fde822e, 740 bytes (this launch class's calldata runs 644-964 bytes in steps of 32, the token name and symbol), value 0. One deployer, 0x06cb3a68 (nonces 1942-1960), Oct 9 02:43-04:13 UTC. It creates a token and a single-sided TOKEN position (132800..201800 at tick 201800, L 3.2e22, no ETH) at fee 1%. 0x78ba8b21 launched 20 pools in all (calldata 740/772/804).",
    "first_buy": "5 of 5 pools: only the chain-wide dust bot 0xe71a69f4, 2e-6 ETH via the Universal Router at +2/+3. Nothing else, and no buy >= 0.0002 ETH (0/5; 0/20 for the launcher).",
    "pull": "0 of 5 pulled. There is no ETH to pull: the position is token-only, and none of the class's 490 pools was pulled in 3,000 blocks.",
    "outsiders": "None besides the dust bot, which is excluded. No pulls, so the trap test is empty.",
    "front_rule": rule(f["front"], ". The 1% fee each way plus gas: every trade -2.06%."),
    "follow_rule": "n 0: no buy of >= 0.0002 ETH.",
    "capacity": "n/a: no scheduled buy.",
    "engine_config": "Not worth trading. The class's recognizer is selector 7fde822e (27 launch contracts) with value 0 and a token-only range; the launch carries no ETH.",
    "verdict": "no-schedule", "candidate_score": 0,
    "notes": ("Wider class (selector 7fde822e, 27 launch contracts, 454 of 490 pools by 0x06cb3a68): %d pools (%.0f a day). Only %d had a buy >= 0.0002 ETH (at +3..+1625, by 5 unrelated wallets through 5 routers), 0 were pulled, and %.4f ETH was bought in 48 h. Front on the class: %s; follow: %s. This is a token-spam deployer: zero-ETH pools that only the dust bot touches. It agrees with every other 7fde822e family the other analyse_* agents scored (all no-schedule)."
              % (W4["count"], W4["launches_per_day"], W4["first_buy_real"]["pools_with"], W4["swaps_non_launch"]["eth_in"], rule(W4["front"]), rule(W4["follow"])))})
bb = CV["bot_buy"]
fam.append({
    "key": "CONTROL vbot-v2.433: 0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true at value 2.4333285 ETH", "known": "vbot-v2.433",
    "count": CV["count"], "launches_per_day": CV["launches_per_day"],
    "launcher": "POSM multicall ac9650d8, 1,444 bytes, exactly 2.4333285 ETH, fee 2500, tick spacing 50, full range, L 4.93e22; a fresh wallet per launch (1843 deployers, nonce median 10).",
    "first_buy": "The bot's router buy (0x1cbaf24d c1120e3d) came in %d/%d pools (%.1f%%), offset p10/50/90 %s blocks, size %s ETH, from %d wallets. Its minOut / launch-state quote p10/50/90 is %s. The first buy >= 0.0002 of any kind (decoys 0x65050a9b included) came at %s blocks."
                 % (bb["pools_with"], CV["count"], 100 * bb["frac"], bb["off_p10_50_90"], bb["eth_p10_50_90"], bb["n_from"], bb["minout_over_launch_quote_p10_50_90"], CV["first_buy_real"]["off_p10_50_90"]),
    "pull": "%.1f%% pulled within 3,000 blocks, offset from launch p10/50/90 %s, from the bot's buy %s (histogram %s), all by the launch wallet through 0x1cbaf24d a0f7978d."
            % (100 * CV["pull"]["frac"], CV["pull"]["off_launch_p10_50_90"], bb["pull_minus_bot_buy_p10_50_90"], bb["pull_minus_bot_buy_hist"]),
    "outsiders": "Before the first real buy: %d pools with buys by others, nearly all the operator's own decoys (0xb002e8a0, 0xf6e55480, 0x488faf52; ~0.00012 ETH). Pull after them p10/50/90 %s vs %s without; this is not a clean trap test, since the decoys are the operator's." % (CV["trap"]["pools_with_outsider_before_sched"], CV["trap"]["delay_after_outsider_p10_50_90"], CV["trap"]["pull_off_without_p10_50_90"]),
    "front_rule": "Sold one block after the bot's buy (else at +20): " + rule(C["v2433_front_bot_sched_all"]) + ". Live window Oct 10 09:07-11:39: " + rule(C["v2433_front_livewindow_oct10_0907_1139"]) + ". The pricer is CALIBRATED: median +14.01%%, live +13.95%%. Our 1,080 real relay round trips re-priced by the model: mean %.3f%% vs real %.3f%%, median abs diff 3e-16. With the generic schedule (first buy >= 0.0002, decoys included): %s." % (100 * C["live_relay_calibration (our real relay round trips re-priced by the model, gross)"]["model_mean"], 100 * C["live_relay_calibration (our real relay round trips re-priced by the model, gross)"]["real_mean"], rule(CV["front"])),
    "follow_rule": rule(CV["follow"], ". The pull 3 blocks after the bot's buy beats a follow exit."),
    "capacity": "minOut decoded (calldata word 4) = 0.99 x the launch-state quote. ETH that can sit ahead of the bot's buy, p10/50/90: %s." % C["v2433_capacity_p10_50_90"],
    "engine_config": "Live: front (HANDOFF 3.2).", "verdict": "control-known", "candidate_score": 0,
    "notes": "This census window has 1843 v2.433 launches in 48 h (921 a day)."})
fam.append({
    "key": "CONTROL operator-A: launcher 0x3194e32622c5d860a0572c74edda99dcfd8fc827, 2fcb9108, 644 bytes (77 pools in 67 strict fee families)", "known": "operator-A",
    "count": CA["count"], "launches_per_day": CA["launches_per_day"],
    "launcher": "To 0x3194e326, 2fcb9108, 644 bytes, value 1.7-3.16 ETH, fee varies (500-4000+), a fresh wallet per launch (nonce 0).",
    "first_buy": "The first real buy came in %d/%d pools, offset p10/50/90 %s blocks, size %s ETH, via the Universal Router (1,124-byte execute), from %d crowd wallets." % (CA["first_buy_real"]["pools_with"], CA["count"], CA["first_buy_real"]["off_p10_50_90"], CA["first_buy_real"]["eth_p10_50_90"], CA["first_buy_real"]["n_from"]),
    "pull": "%.1f%% pulled within 3,000 blocks, from launch p10/50/90 %s, from the first real buy %s, by the launch wallet through POSM dd46508f." % (100 * CA["pull"]["frac"], CA["pull"]["off_launch_p10_50_90"], CA["pull"]["off_from_first_real_buy_p10_50_90"]),
    "outsiders": "%d pools had small outsider buys (mostly 0xf7b47b17, 6e-5 ETH). Pull after them p10/50/90 %s vs from launch without %s." % (CA["trap"]["pools_with_outsider_before_sched"], CA["trap"]["delay_after_outsider_p10_50_90"], CA["trap"]["pull_off_without_p10_50_90"]),
    "front_rule": rule(CA["front"], ". At the 20-block cap it sells before the crowd arrives (median +54). Without the cap: " + rule(CA["front_no20cap (sell 1 block after the first real buy, deadline +3000)"]) + "."),
    "follow_rule": rule(CA["follow"], ". This matches the live follow results (HANDOFF 3.1: +2-4%)."),
    "capacity": "UR execute (nested) is not decoded: ASSUMED minOut = 0.99 x the launch-state quote, room p10/50/90 %s ETH." % CA["capacity"]["cap_eth_p10_50_90"],
    "engine_config": "Live: follow (HANDOFF 3.1).", "verdict": "control-known", "candidate_score": 0, "notes": ""})
json.dump({"families": fam}, open(os.path.join(HERE, "families_out.json"), "w"), indent=1)
print(json.dumps({"families": fam}, indent=1))
