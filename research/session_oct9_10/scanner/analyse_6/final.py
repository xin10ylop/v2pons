"""Assemble families_out.json (the structured output) from results.json, calib*.json, context.json, postwindow.json, decode.json."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "results.json"))); C = json.load(open(os.path.join(HERE, "calib_periods.json")))
PW = json.load(open(os.path.join(HERE, "postwindow.json")))
def fr(s): return (f"n {s['n']}, mean {100*s['mean']:+.2f}%, median {100*s['median']:+.2f}%, win {100*s['win']:.0f}%, pulled-first {s['pulled_first']}, "
                   f"${s['usd_trade']:+.3f} a trade, ${s['usd_day']:+.2f} a day at $15 ({s['trades_day']} trades/day over the 48 h census)") if s["n"] else "n 0"
L7 = ("deployer EOA 0x06cb3a6841c92525e7a1998328e7c9d37e98d937 alone (type-2, tip 0, gas ~1.70M, value 0) calls {to} (19,030-byte contract; one of 27 near-identical "
      "launch contracts it rotates through, ~20 launches each) with 7fde822e(name, symbol, image URL on imortal.buzz, x.com/website, constant 0x94dddbb54535ee3515b3b9e10be5a6569c586324 twice, "
      "2500, 1.7e18): it deploys a token and a v4 ETH pool fee 10000 ts 200 hooks 0 at tick 201800 with token-only liquidity 3.2156e22 in [132800, 201800] (no ETH in the pool). "
      "Clockwork: one launch every ~2,900 blocks (~5 min) across all its contracts, 454 launches in the 48 h window (nonces 1837-2312).")
out = []
for k, to, nonces in ((list(R)[0], "0x404700be6b535e6aa7fd744f242d8cf78135817c", "2174-2191"), (list(R)[1], "0xe696daf67fe25c5936187fc1edf38404353d5f72", "2258-2276"),
                      (list(R)[2], "0xb40382548413c559ad7f0bb6e24410401238eded", "2131-2150")):
    r = R[k]; pw = PW["per_family"][k]
    out.append({"key": k, "known": "none", "count": r["count"], "launches_per_day": r["launches_per_day_window"],
        "launcher": L7.format(to=to) + f" This contract's {r['count']} launches: nonces {nonces}, gaps p10/50/90 {r['launch_gap_blocks_p10_50_90']} blocks.",
        "first_buy": (f"{r['first_buy']['pools_with']}/{r['count']} pools: the chain-wide dust bot 0xe71a69f434a719cd5afa411568b69716aab3b84a only (one wallet, Universal Router 3593564c), "
                      f"offset p10/50/90 {r['first_buy']['rel_p10_50_90']} blocks, size 2.0e-6 ETH; no other buy of any size in any pool within 3,000 blocks; first buy >= 0.0002 ETH: 0/{r['count']}. "
                      f"RPC check to head {PW['head']}: still nothing else ever ({pw['total_eth_in']} ETH in all, pools {pw['age_blocks_min']}+ blocks old)."),
        "pull": f"0/{r['count']} within 3,000 blocks and 0 ever to the head (RPC); the liquidity is token-only, so there is no ETH to pull.",
        "outsiders": "none besides the dust bot (2e-6 ETH at +3 in every pool); no scheduled buy and no pull, so the trap test is not applicable.",
        "capacity": "n/a: no scheduled buy exists (no buy >= 0.0002 ETH ever).",
        "front_rule": fr(r["front"]) + "; every sell at launch +20 (no scheduled buy): the cost of two 1% fees plus gas.",
        "follow_rule": "n 0: no buy >= 0.0002 ETH in any pool (window or ever), so no trigger; $0.",
        "engine_config": "none: nothing to trade (recognizer would be to=" + to + ", selector 7fde822e, 804 bytes, value 0; but no scheduled buy exists).",
        "verdict": "no-schedule", "candidate_score": 0,
        "notes": ("Part of the loose 7fde822e launcher type: 490 pools on 27 contracts in the window, 454 by this deployer; across all 490: 0 pulls, 5 pools with any buy >= 0.0002 ETH "
                  "(one buy each, 0.0012-0.0107 ETH at +3 (one pool) or +843..+1625, five unrelated wallets through five different routers). A token-factory spam/launchpad deployer whose pools nobody trades. Pricing: exact v4math replay, fee 10000 applied.")})
k4 = list(R)[3]; r = R[k4]; pw = PW["per_family"][k4]
out.append({"key": k4, "known": "none", "count": r["count"], "launches_per_day": r["launches_per_day_window"],
    "launcher": ("8 different EOAs (0x21debf9f 4, 0x26e8134e 2 (nonce 63,507), 0x0551dcb0, 0x28e7b7fe, 0xc085e994, 0x178a859a, 0x27fd5e05, 0x4fbdeda7), value 0, irregular "
                 f"(gaps p10/50/90 {r['launch_gap_blocks_p10_50_90']} blocks), calling the public helper 0x0000ffffbe8efe702c8703ae3477ff5de3d319c0 (4,127 bytes) multicall ac9650d8 "
                 "of [token deploy dec14be1 through factory 0xe200088d55c39a11f609e5f667729ad49b..., 1e27 supply; POSM mint]: v4 pool fee 2500 ts 25 hooks 0 at tick 198050, "
                 "token-only liquidity 5.0074e22 in [-160100, 198050]; applied swap fee 2899 ppm (400 ppm protocol fee). The helper served 36 deployers / 66 pools in the window "
                 "(values 0, 1.5, 0.005 ETH), none pulled within 3,000 blocks: retail launches, not one operator."),
    "first_buy": (f"{r['first_buy']['pools_with']}/{r['count']} pools: the dust bot 0xe71a69f4 at +3 (p10/50/90 {r['first_buy']['rel_p10_50_90']}), 2.0e-6 ETH via the Universal Router. "
                  "Next buys: the launch wallets themselves, 4e-5 to 8.4e-5 ETH at +681, +1,092, +1,124 (3 pools); first buy >= 0.0002 ETH within 3,000 blocks: 0/12. "
                  f"RPC to head {PW['head']}: two later buys >= 0.0002 ETH, 0.0062 ETH at +10,465 (sold back at +13,640) and 0.0060 ETH at +153,706; {pw['total_eth_in']} ETH in all."),
    "pull": "0/12 within 3,000 blocks and 0 ever to the head (RPC); token-only liquidity.",
    "outsiders": "only the dust bot before any later buy; no scheduled buy and no pull: trap test not applicable.",
    "capacity": "n/a: no scheduled buy.",
    "front_rule": fr(r["front"]) + "; every sell at launch +20: two 0.29% fees plus gas.",
    "follow_rule": "n 0 within the census window (no buy >= 0.0002 ETH in 3,000 blocks); the two later buys come 10k and 154k blocks in, singly; $0.",
    "engine_config": "none.", "verdict": "no-schedule", "candidate_score": 0,
    "notes": "Many unrelated deployers using one public launch helper; no operator schedule, no pulls, no crowd."})
v = R["control:vbot-v2.433"]; P_ = C["periods"]
out.append({"key": "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true", "known": "vbot-v2.433 (control)", "count": v["count"], "launches_per_day": v["launches_per_day_window"],
    "launcher": "a fresh wallet per launch (1,843 deployers) through POSM multicall, 2.4333285 ETH; bursts (gaps p10/50/90 162/173/3,597 blocks); Oct 10 surge.",
    "first_buy": ("first non-launch buy: the dust bot 0xe71a69f4 (940) or the operator's decoy router 0x65050a9b (854) at +2/3/3; the scheduled buy (router 0x1cbaf24d c1120e3d, "
                  f"a different wallet each time) at +{v['sched']['rel_p10_50_90']} blocks, {v['sched']['eth_p10_50_90']} ETH, in 1,842/1,843 pools."),
    "pull": (f"{100*v['pull']['frac']:.1f}% within 3,000 blocks; +{v['pull']['rel_p10_50_90']} from launch, +{v['pull']['after_sched_p10_50_90']} after the bot's buy; "
             "all 1,482 by the launch wallet through the router (a0f7978d)."),
    "outsiders": ("buys before the bot's buy other than dust/decoy routers in 5 of 1,842 pools (2e-5..5e-5 ETH); pull after the bot's buy with one 8/27/30 (n 3) vs 3/3/117 without "
                  "(n 1,478): too few to call. But see notes: since Oct 10 14:51 UTC its own wallets front the bot's buy."),
    "capacity": (f"real minOut from calldata word 4 = exactly 0.99 x the launch-state quote in all 1,842 (every era); total ETH that can sit ahead p10/50/90 "
                 f"{[round(x, 4) for x in v['sched']['room_from_launch_eth_p10_50_90']]}; room left before the bot's buy 0.0123/0.0125/0.0128 before live, "
                 f"{[round(x, 4) for x in C['room_left_eth_p10_50_90']['c_defense_era']]} since 14:51 UTC (under 0.0058 in 229 of 574)."),
    "front_rule": (fr(v["front"]) + f". By period: before our live trading {fr(P_['a_before_live'])}; live, before 14:51 UTC {fr(P_['b_live_before_defense'])} "
                   f"(live audit +14.0% mean / +16.25% median: pricer calibrated); since 14:51 UTC {fr(P_['c_defense_era'])}, 229 bot buys revert with our $15 ahead."),
    "follow_rule": fr(v["follow"]) + ": not its rule (triggers on the 0.00495 decoys, pull 3 blocks after the bot).",
    "engine_config": "live as front (HANDOFF 3.2).", "verdict": "control-known", "candidate_score": 0,
    "notes": ("NEW since Oct 10 14:51 UTC (block ~85.08M): in 510 of 574 pools wallets 0x488faf52/0x544ef435/0xe322fc6d (router 0x65050a9b, the operator's decoy router; 0x488faf52 "
              "is the decoy funder of HANDOFF section 1) buy 0.00495 ETH at +1..+2 and 0xb4c345dc (router 0xfd1b271f) 0.002475-0.00495 at +2..+3, and both SELL one block after the bot's buy: "
              "the front trade itself, 0.0074-0.0099 ETH of the ~0.0127 room. On the chain our relay sold on their 0.00495 buys at +2/+3 for about +0.3% (FRONT_SELL_ON_ETH 0.004 then); "
              "holding to the bot's buy, our $15 would revert the bot's buy in 229/574 pools. Stake sweep since then: 0.002 ETH +13.2% mean, 0.004 +9.6%, 0.0058 +7.8% (calib_periods.json).")})
a = R["control:operator-A"]
out.append({"key": "operator-A (to 0x3194e32622c5d860a0572c74edda99dcfd8fc827 or selector 2fcb9108; 67 strict families)", "known": "operator-A (control)", "count": a["count"],
    "launches_per_day": a["launches_per_day_window"],
    "launcher": "operator A's launcher 0x3194e326 (2fcb9108), a fresh wallet per launch (77 deployers), fee varies per launch.",
    "first_buy": (f"first non-launch buy: the dust bot at +3 (74/77); first real buy (crowd, Universal Router) +{a['first_real_buy']['rel_p10_50_90']} blocks, "
                  f"{a['first_real_buy']['eth_p10_50_90']} ETH, 10 distinct wallets, 75/77 pools."),
    "pull": (f"{100*a['pull']['frac']:.1f}% within 3,000; +{a['pull']['rel_p10_50_90']} from launch, +{a['pull']['after_sched_p10_50_90']} after the first real buy; "
             "all 66 by the launch wallet through POSM dd46508f."),
    "outsiders": (f"non-dust buys before the first real buy in 27 pools (4e-5..6e-5 ETH); pull after the first real buy with one {a['outsiders']['pull_after_sched_with_outsider_p10_50_90']} (n 25) "
                  f"vs {a['outsiders']['pull_after_sched_without_outsider_p10_50_90']} without (n 41): not sooner at these sizes."),
    "capacity": f"minOut not decodable (Universal Router execute, nested): assumed 0.99 x launch-state quote: {[round(x, 4) for x in a['sched']['room_from_launch_eth_p10_50_90']]} ETH (assumption).",
    "front_rule": fr(a["front"]) + ": the crowd comes after +20.",
    "follow_rule": fr(a["follow"]) + "; hold 2 +0.2%, hold 3 +3.2%, hold 6/10 +2.1%/+2.4% with 2 pulled (calib.json): matches the live +2-4%.",
    "engine_config": "live as follow (HANDOFF 3.1).", "verdict": "control-known", "candidate_score": 0, "notes": "Pricer calibration control."})
json.dump({"families": out}, open(os.path.join(HERE, "families_out.json"), "w"), indent=1)
print(json.dumps({"families": out}, indent=1)[:6000])
