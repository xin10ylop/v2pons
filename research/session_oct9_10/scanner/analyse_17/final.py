"""Assemble results.json for the orchestrator from stats.json, trapA.json, calib.json, calib_front.json, hooktax.json (numbers quoted below
were read from those files; rerun: hookfee17.py, hooktax17.py, analyse17.py, calib17.py, stats17.py, trapA.py, calib_front.py, final.py)."""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
ST = json.load(open(os.path.join(HERE, "stats.json"))); K = json.load(open(os.path.join(HERE, "keys.json")))
TA = json.load(open(os.path.join(HERE, "trapA.json"))); CF = json.load(open(os.path.join(HERE, "calib_front.json"))); CL = json.load(open(os.path.join(HERE, "calib.json")))


def rule(s):
    if not s.get("n"): return f"n 0 ({s.get('exits')})"
    return (f"n {s['n']}, mean {100*s['mean']:+.2f}%, median {100*s['median']:+.2f}%, win {100*s['win']:.0f}%, pulled-first {s['pulled_first']}, "
            f"${s['usd_trade']:+.3f} a trade, ${s['usd_day']:+.2f} a day ({s['trades_day']}/day)")


method = ("Pricer common17.py = analyse_15/common15.py verbatim (the replay.py model on the census) plus a per-pool ETH-side hook tax for hook 0x75a54357. "
          f"Calibrated against our relay's own live trades: v2.433 {CL['vbot-v2.433']['n_priced']} trades, median |sim-real| {CL['vbot-v2.433']['abs_diff_median']:.1e}, all within 0.5 pt; "
          f"operator A {CL['operator-A']['n_priced']} follow trades, exact. Front control v2.433 (1,843 pools): {rule(ST['control:vbot-v2.433']['front'])}; "
          f"launched in the live window Oct 10 09:07-11:40: {rule(CF['launched_Oct10_09:07-11:40'])} (live audit HANDOFF 16.2: +13.97% mean, +16.25% median); "
          f"bot buy >= 0.04 ETH: {rule(CF['bot_buy_ge_0.04_by_+19'])}. Follow on v2.433: {rule(ST['control:vbot-v2.433']['follow'])} (the pull 3 blocks after the bot's buy beats a buy+1 entry). "
          f"Operator A all 77 pools: follow {rule(ST['control:operator-A']['follow'])}; front {rule(ST['control:operator-A']['front'])} (crowd comes after +20).")

fam = []
s = ST[K[0]]; t = TA[K[0]]; tc = TA["control:operator-A"]
fam.append({
    "key": K[0], "known": "operator-A (original launcher 0x3194e326, its 0.15% fee tier; the engine's follow target)", "count": 6, "launches_per_day": 3.0,
    "launcher": "launcher contract 0x3194e326 (2fcb9108, 644-byte calldata, value 1.55/1.6/2.35/2.7 ETH), 6 distinct fresh launch wallets at nonce 0; launched Oct 9 17:35 - Oct 10 09:18 UTC (15.7 h)",
    "first_buy": ("first non-launch buy of any size: +3 in 6/6, 2e-6 ETH by the chain-wide dust bot 0xe71a69f4 via the UR (5) and a 0.000119 ETH 0x65050a9b decoy (1). "
                  f"First real buy (>= 0.0002, the operator's crowd): 6/6 pools, offset p10/50/90 {s['first_real']['rel']} blocks, size {s['first_real']['eth']} ETH, all Universal Router execute "
                  "1124-byte calldata, 4 recurring crowd wallets (0xdc2e8661 x3, 0x8700722d, 0x295877ce, 0x75442507; nonces 448-2071), no fresh wallets"),
    "pull": (f"6/6 pulled within 3000 blocks, all the liquidity, by the launch wallet via POSM modifyLiquidities dd46508f; offset from launch p10/50/90 {s['pull']['rel']}, "
             f"from the first crowd buy {s['pull']['from_sched']}, from our relay's live follow buy {s['pull']['from_first_relay_buy']}"),
    "outsiders": ("no real-size outsider before the first crowd buy in 0/6 pools (only dust: 2e-6 at +3, 8.3e-6 at +19, 4e-5 at +14, 0.000119 decoy at +3). "
                  "Trap test with the only real outside buys there are, our relay's live follow buys: in this family the pull came "
                  f"{t['with_relay_pull_from_relay_buy']} blocks after our buy in 6/6 pools. Over all 77 operator-A pools: with our relay buy {tc['with_relay_pulled']}/{tc['pools_with_relay_buy']} pulled, "
                  f"{tc['with_relay_pull_within_6_of_relay']} within 6 blocks of our buy, pull from the first crowd buy p10/50/90 {tc['with_relay_pull_from_first_crowd']}; without our buy "
                  f"{tc['without_relay_pulled']}/{tc['pools_without']} pulled, from the first crowd buy {tc['without_relay_pull_from_first_crowd']}, 0 of 38 within 12 blocks. "
                  "The operator pulls ~5 blocks after an outside buy: a TRAP for any entry before the crowd"),
    "front_rule": (f"{rule(s['front'])}: the crowd's first buy is at +22..+50, never by +19, so every trade sells at +20 into nobody (two 0.15% fees + gas). "
                   f"Without the +20 cap (sell one block after the first crowd buy): {rule(s['front_wait'])} in the replay, which cannot see the pull our launch+1 buy would provoke "
                   "(5-6 blocks after an outside buy here) 20-50 blocks before the crowd: not tradeable"),
    "follow_rule": f"{rule(s['follow'])} (exits all 'sold'; 3 up +2.3..+7.4%, 3 flat -0.37% with no crowd buy before buy+4); the pull came 5-6 blocks after our live buy, so the buy+4 exit has 1-2 blocks of margin",
    "capacity": ("Universal Router execute is nested: minOut not decoded. ASSUMED minOut = 0.99 x launch-state quote: ETH ahead of the first crowd buy before its fill falls under it "
                 f"p10/50/90 {s['cap']['cap_from_launch']} ETH (at its actual pre-trade state {s['cap']['room_left']}); its real fill was {s['cap']['actual_over_launch_quote']} of the launch quote"),
    "engine_config": ("already in the engine as follow (ENTRY=auto, original launcher): recognize to 0x3194e326 sel 2fcb9108 (644 bytes, value 1.5-2.7 ETH), fee 1500 ts 200 hooks 0, "
                      "full-range liquidity; trigger = first buy >= 0.0002 ETH (UR execute, crowd) within 150 blocks; buy lands at trigger+1; exit at the next crowd buy (TP) or buy+4; stake <= ~0.008 ETH"),
    "verdict": "control-known", "candidate_score": 0,
    "notes": ("Calibration: the pricer reproduces our 35 live operator-A follow trades exactly. The operator has not launched since Oct 10 09:56 (HANDOFF 16.4); "
              "this fee tier's 6 launches are all in Oct 9 17:35 - Oct 10 09:18.")})

s = ST[K[1]]
fam.append({
    "key": K[1], "known": "none (literal-rule vbot-other: the standard POSM create-and-mint multicall; no sign of the volume bot)", "count": 6, "launches_per_day": 3.0,
    "launcher": "POSM 0x58daec31 multicall ac9650d8 (1444 bytes), value 1.2e-5..4.1e-4 ETH, 4 wallets (0xd6ea056b x3, 0xc6312da2, 0x45fcadcb, 0xe620839e) with nonces 898-3666; Oct 9 00:18 - Oct 10 02:16; tiny full-range liquidity (L 1.5e17..9e19), 60% LP fee",
    "first_buy": "any buy in 1/6 pools only: 1.75e-6 ETH at +441 via 0xf69cd0fe (69508f86); no buy >= 0.0002 ETH in 0/6",
    "pull": "1/6 within 3000 blocks (+2632, half the liquidity, by the launch wallet via POSM dd46508f); no first buy to measure from",
    "outsiders": "no scheduled buy, no outsider: nothing to test",
    "front_rule": f"{rule(s['front'])}: the 60% LP fee each way on a pool nobody trades",
    "follow_rule": "n 0: no buy >= 0.0002 ETH in any pool",
    "capacity": "n/a (no scheduled buy)",
    "engine_config": "none: fee 600000 (60%) makes any round trip lose ~60%",
    "verdict": "no-schedule", "candidate_score": 0,
    "notes": "Spam/test pools (dust values, near-zero liquidity, 60% fee); the 2020-byte sibling (30 pools) is another agent's."})

s = ST[K[2]]
fam.append({
    "key": K[2], "known": "none (public launchpad 0x5bd1fbe7, 176-byte proxy; hook 0x75a54357)", "count": 6, "launches_per_day": 3.0,
    "launcher": ("launchpad 0x5bd1fbe7 a80ac0c2 (calldata 1156-1444 bytes with the token metadata; the whole launchpad: 21 pools in the 2-day window), 6 distinct fresh creators (nonce 0-1), "
                 "value 0.0005-3.2 ETH = an optional dev buy inside the launch tx (4/6: 0.019-3.16 ETH); PoolKey fee 0, hook 0x75a54357 takes a per-launch tax on the ETH in (buys) and the ETH out "
                 "(sells): 1% (2 pools), 3% (2), 5% (2), read from the launch receipts (event 0xcf68bf26 word 2) and checked on 34 swap receipts; liquidity [-887200, 204200] placed by the launchpad, never pulled"),
    "first_buy": (f"first non-launch buy (all real): 5/6 pools, offset {sorted([1, 4, 241, 253, 314])} (p10/50/90 {s['first_real']['rel']}), size p10/50/90 {s['first_real']['eth']} ETH; "
                  "routers UR execute (3), 0x9689992f 3e0f9c3c (1), 0xb1000000 549299b8 (1); 4 distinct wallets (nonces 0-7664): unrelated snipers/traders, no schedule"),
    "pull": "0/6 pulled within 3000 blocks (the launchpad holds the liquidity)",
    "outsiders": "no operator schedule, so every buyer is an outsider; no pull ever, so no trap to test",
    "front_rule": (f"{rule(s['front'])} (1 pool sniped with 2.47 ETH at +1 before our buy: no trade); the hook's 1-5% tax each way plus no scheduled buyer: "
                   f"4 of 5 sell at +20 into nobody. Sell-on-first-buy without the +20 cap: {rule(s['front_wait'])}"),
    "follow_rule": f"{rule(s['follow'])}",
    "capacity": ("no scheduled buy with a known minOut (UR nested; routers 0x9689992f / 0xb1000000 not decoded). ASSUMED 0.99 x launch-state quote: "
                 f"{s['cap']['cap_from_launch']} ETH ahead of the first buy; meaningless without a schedule"),
    "engine_config": "none: a public launchpad (fresh creators, random snipers), 1-5% hook tax each way, no scheduled buyer",
    "verdict": "no-schedule", "candidate_score": 0,
    "notes": "Fee-0 PoolKey hides the hook's ETH tax: priced with it (hooktax.json). The 1156-byte sibling family was analysed by analyse_12."})

s = ST[K[3]]
fam.append({
    "key": K[3], "known": "none (one of the ~27 launch contracts of the 7fde822e operator, deployer 0x06cb3a68)", "count": 6, "launches_per_day": 3.0,
    "launcher": ("contract 0x78ba8b21 (19,036 bytes) 7fde822e, 772 bytes, value 0, one wallet 0x06cb3a68 (nonces 1943-1961; it made 454 of the operator's 490 pools, 245 a day over 27 contracts); "
                 "6 launches Oct 9 02:47-04:17 UTC; single-sided token range [132800, 201800] at its upper edge, L 3.2e22"),
    "first_buy": "6/6: only the chain-wide dust bot 0xe71a69f4, 2e-6 ETH at +3 via the UR; no buy >= 0.0002 ETH in 0/6 (the whole 7fde822e operator: 5 of 490 pools)",
    "pull": "0/6 pulled within 3000 blocks (whole operator: 0/490)",
    "outsiders": "no scheduled buy, no real outsider: nothing to test",
    "front_rule": f"{rule(s['front'])}: sells at +20 into nobody, two 1% fees",
    "follow_rule": "n 0: no buy >= 0.0002 ETH",
    "capacity": "n/a (no scheduled buy)",
    "engine_config": "none",
    "verdict": "no-schedule", "candidate_score": 0,
    "notes": "Token-minting spam with no buyer and no pull."})

out = {"method": method, "families": fam,
       "controls": {"vbot-v2.433": {k: ST["control:vbot-v2.433"][k] for k in ("count", "launches_per_day_window", "sched", "pull", "trap", "front", "front_wait", "follow", "cap")},
                    "vbot-v2.433_front_splits": CF,
                    "operator-A": {k: ST["control:operator-A"][k] for k in ("count", "launches_per_day_window", "first_real", "pull", "front", "front_wait", "follow", "cap")},
                    "operator-A_trap": TA, "calib_live": {k: {a: CL[k][a] for a in ("n", "n_priced", "real_mean", "sim_matched_mean", "abs_diff_median", "within_0.5pt")} for k in CL}}}
json.dump(out, open(os.path.join(HERE, "results.json"), "w"), indent=1, default=str)
print(method); print(json.dumps(fam, indent=1)[:6000])
