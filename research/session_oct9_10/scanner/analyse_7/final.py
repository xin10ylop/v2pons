"""assemble families_out.json (the structured output) and results.json from stats.json, calib*.json, trap_v2433.json, loose7fde.json, postwindow.json"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common7 import *  # noqa
S = json.load(open(os.path.join(HERE, "stats.json"))); C = json.load(open(os.path.join(HERE, "calib.json")))
CL = json.load(open(os.path.join(HERE, "calib_live.json"))); TR = json.load(open(os.path.join(HERE, "trap_v2433.json")))
LO = json.load(open(os.path.join(HERE, "loose7fde.json"))); PW = json.load(open(os.path.join(HERE, "postwindow.json")))
F = load_families(); KEYS = json.load(open(os.path.join(HERE, "families_in.json")))
pct = lambda x: f"{100*x:+.2f}%"
CALIB = (f"Pricer calibration (same code): v2.433 front in the live window (Oct 10 09:07-11:40 UTC, 409 pools) {pct(C['v2433_live_window']['mean'])} mean / "
         f"{pct(C['v2433_live_window']['median'])} median / {100*C['v2433_live_window']['win']:.1f}% win; pool by pool against the {CL['n']} priced live relay trades "
         f"(their real stake and buy/sell blocks) the pricer's gross return equals the realised one to {abs(CL['median_diff_gross_minus_live']):.0e}; operator A follow "
         f"{pct(C['opA_follow']['mean'])} (n {C['opA_follow']['n']}).")
LOOSE = (f"The whole 7fde822e launcher (all {LO['pools']} pools on {LO['launch_contracts']} launch contracts, 5 deployers, 454 by 0x06cb3a68) prices the same: front "
         f"{pct(LO['front']['mean'])} on {LO['front']['n']}/{LO['pools']} (win 0), follow {pct(LO['follow']['mean'])} on the {LO['follow']['n']} pools that ever got a buy >= 0.0002 ETH "
         f"(+3, +843, +959, +1510, +1625 blocks, 0.0012-0.0107 ETH, five different buyers/routers), 0 pulled.")
out = []
for k in KEYS:
    s = S[k]; f = F[k]; fam = k.split("|")[0]
    fr = s["fr"]; one = fr.get("pools", 0) > 0
    fb = s["fb"]
    row = {
        "key": k, "known": "none", "count": s["n"], "launches_per_day": s["launches_per_day"],
        "launcher": (f"one EOA 0x06cb3a6841c92525e7a1998328e7c9d37e98d937 (nonces {s['launch_nonce_p10_50_90'][0]}-{s['launch_nonce_p10_50_90'][2]} here) calling its own launch "
                     f"contract {fam} ({f['to_code_size']} bytes, code hash {f['to_code_hash'][:8]}...) with 7fde822e, 804-byte calldata, value 0, tip 0, gas limit ~1.70M. The calldata is "
                     f"token metadata from the imortal.buzz launchpad (name, symbol, an imortal.buzz/i/<ipfs cid> image, x.com and t.co links), the same creator/fee address "
                     f"0x94dddbb54535ee3515b3b9e10be5a6569c586324 in all 48, the constant 2500 and 1.7 ETH (apparently the starting valuation: tick0 201800 prices 1e9 tokens at ~1.72 ETH; the range holds ~749M tokens). Pool: fee 1%, ts 200, hooks 0, one "
                     f"token-only range [132800, 201800] at tick0 201800, L 32156000099526845215062 (no ETH in the pool; virtual ETH depth L/sqrtP = 1.34 ETH). This contract served "
                     f"{s['n']} launches in {s['active_hours']} h (blocks {s['span_blocks'][0]}-{s['span_blocks'][1]}, gap p10/50/90 {s['gap_blocks_p10_50_90']} blocks), then the wallet "
                     f"moved to a new contract (27 contracts, 490 launches by 5 deployers in 48 h; 0x06cb3a68 alone 454 = 227/day, one every ~2,922 blocks)."),
        "first_buy": (f"first non-launch buy in {fb['pools']}/{s['n']}: the chain-wide dust bot 0xe71a69f4 (one wallet, it buys every new pool on the chain) via the Universal Router "
                      f"execute, offset p10/50/90 {fb['off_p10_50_90']} blocks, size {fb['eth_p10_50_90']} ETH; sender diversity 1 wallet, not fresh. First buy >= 0.0002 ETH: "
                      + (f"{fr['pools']}/{s['n']} pools: 0.0042978 ETH at +959 from 0x329ca263 via 0x5399d94d (selector 814920c0, value 0), and 2 blocks later 0x94dddbb5 (the "
                         f"launch calldata's creator/fee address) sold exactly the same 2,461,071 tokens via 0xfa9b5811 (bbb2e1a6): a one-off, not a schedule. "
                         if one else f"0/{s['n']}. ")
                      + f"Fraction of pools with a scheduled operator buy: 0. RPC check to head {PW['head']}: no swap after the 3,000-block window in any of the 48 pools."),
        "pull": (f"0/{s['n']} pulled within 3,000 blocks and 0/{s['n']} ever (eth_getLogs of every Swap/ModifyLiquidity of my 48 pools from launch to block {PW['head']}, "
                 f"0.7-1.7M blocks later: only the launch mint and the buys above); offsets from launch / first buy n/a; nobody pulls (0 of the launcher's 490 pools in 3,000 blocks)."),
        "outsiders": (f"everyone but the launcher is an outsider here: the dust bot in {s['outsiders']['dust_bot_pools']}/{s['n']} pools (2e-6 ETH at +3)"
                      + (", and the one 0.0043 ETH buyer at +959 in 1 pool" if one else ", no real-size buyer")
                      + "; trap test not computable: 0 pulls with or without outsiders (0/48 ever; 0/490 across the launcher)."),
        "front_rule": fmt_rule(s["front"]) + " (no scheduled buy: every trade sells at +20 into the untouched pool and pays two 1% fees + 0.07% gas)",
        "follow_rule": (fmt_rule(s["follow"]) + " (the one trigger: buy at +960 after the 0.0043 ETH buy, no next buy, sold at +964 after 0x94dddbb5's sell at +961)") if one
                       else "n 0: no buy >= 0.0002 ETH in any pool (0 trades, $0 a day)",
        "capacity": ("n/a: no scheduled buy to decode. Assumption for reference only (minOut = 0.99 x the launch-state quote, 814920c0 calldata not decoded): the one 0.0043 ETH "
                     "buy could carry 0.0068 ETH ahead; any small buy into these pools loses 1% with about 0.0067 ETH ahead (virtual depth 1.34 ETH)") if one else
                    "n/a: no scheduled buy to decode (assumption-only reference: about 0.0067 ETH ahead cuts any small buy's output 1%, virtual ETH depth 1.34 ETH)",
        "engine_config": ("none: nothing to trade. Recognizer if ever needed: from 0x06cb3a6841c92525e7a1998328e7c9d37e98d937, selector 7fde822e, value 0, calldata 644-964 bytes (to = "
                          "its current launch contract, rotates every 12-16 launches); pool fee 10000, ts 200, hooks 0, token-only range at tick0 201800; no exit trigger exists"),
        "verdict": "no-schedule", "candidate_score": 0,
        "notes": ("A launchpad publisher (imortal.buzz user tokens at a 1.7 ETH starting cap), not a pump-and-pull operator: no operator buy, no decoys, liquidity never removed, "
                  "nobody trades the pools. " + LOOSE + " " + CALIB),
    }
    out.append(row)

v = S["control:vbot-v2.433"]; a = S["control:operator-A"]
out.append({
    "key": "control:vbot-v2.433 (0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true, value 2.4333285 ETH)", "known": "vbot-v2.433", "count": v["n"],
    "launches_per_day": v["launches_per_day"],
    "launcher": f"POSM multicall ac9650d8, 1,444 bytes, value exactly 2.4333285 ETH, a fresh wallet per launch ({v['n_launch_wallets']} senders, nonce p10/50/90 {v['launch_nonce_p10_50_90']})",
    "first_buy": (f"first non-launch buy: +{v['fb']['off_p10_50_90']} blocks, {v['fb']['eth_p10_50_90']} ETH (the dust bot via UR in 940 pools, the bot's decoy router 0x65050a9b in 854; "
                  f"{v['fb']['n_from']} senders, {v['fb']['fresh_nonce_le2']} with nonce <= 2). The scheduled buy (router 0x1cbaf24d, c1120e3d) in {v['sb']['pools']}/{v['n']}: offset "
                  f"{v['sb']['off_p10_50_90']}, size {v['sb']['eth_p10_50_90']} ETH, {v['sb']['n_from']} sender wallets (none fresh)."),
    "pull": (f"{v['pull']['pulled']}/{v['n']} ({100*v['pull']['frac']:.0f}%) within 3,000 blocks; from launch {v['pull']['off_launch_p10_50_90']}, from the bot's buy "
             f"{v['pull']['off_sched_p10_50_90']}; all {v['pull']['by_launch_wallet']} by the launch wallet through the bot's router (a0f7978d); 0 before the bot's buy."),
    "outsiders": (f"real outsiders (not the bot's router or decoys, not the dust bot, not our relay) before the bot's buy in {v['outsiders']['pools']}/{v['n']} pools, "
                  f"{v['outsiders']['eth_p10_50_90']} ETH (0xfeda1c58 via 0xf0b7eaaf x4); none >= 0.0001 ETH, so the chain's own trap test is empty. With our relay as the outsider "
                  f"(trap_v2433.json): in the relay's hours (Oct 10 09:08-17:37) {TR['in_relay_hours_with_relay']['within_2_4']} of {TR['in_relay_hours_with_relay']['pulled']} pulled "
                  f"relay pools were pulled 2-4 blocks after the bot's buy vs {TR['in_relay_hours_without_relay']['within_2_4']} of {TR['in_relay_hours_without_relay']['pulled']} pools the "
                  f"relay skipped (p90 {TR['in_relay_hours_without_relay']['pull_minus_sched_p10_50_90'][2]}) and {TR['before_relay_hours']['within_2_4']} of "
                  f"{TR['before_relay_hours']['pulled']} before the relay started (median {TR['before_relay_hours']['pull_minus_sched_p10_50_90'][1]}): the quick pull tracks our trading, "
                  f"but it lands after the bot's buy, so front still sells first."),
    "front_rule": (fmt_rule(v["front"]) + f"; live window (409 pools) {pct(C['v2433_live_window']['mean'])} mean, {pct(C['v2433_live_window']['median'])} median, "
                   f"{100*C['v2433_live_window']['win']:.1f}% win; {v['front']['bot_dropped_pools']} pools where the bot's decoys put 0.0074-0.0099 ETH ahead and our 0.0058 reverts "
                   f"the bot's buy: {pct(C['v2433_bot_buy_dropped']['mean'])}; the other {C['v2433_not_dropped']['n']}: {pct(C['v2433_not_dropped']['mean'])}"),
    "follow_rule": fmt_rule(v["follow"]) + " (the pull 3 blocks after the bot's buy beats a sell at our buy + 4)",
    "capacity": (f"real minOut (calldata word 4) on {v['capacity']['real_minout']}: minOut / launch-state quote {v['capacity']['minout_vs_quote_p10_50_90']}; total ETH allowed ahead from "
                 f"the launch state {v['capacity']['room_from_launch_p10_50_90']}; after the decoys' actual pre-buys {v['capacity']['room_after_prebuys_p10_50_90']}; "
                 f"{v['capacity']['room_lt_stake']} pools with less room than 0.0058"),
    "engine_config": "the live front engine: to POSM, ac9650d8, 1,444 bytes, value 2.4333285 ETH; fee 2500, ts 50, hooks 0; fire in the launch block (lands +1); exit on any buy through 0x1cbaf24d; deadline buy + 18",
    "verdict": "control-known", "candidate_score": 0,
    "notes": CALIB + " By 6 h: " + json.dumps(C["v2433_by_6h"]),
})
out.append({
    "key": "control:operator-A (0x3194e32622c5d860a0572c74edda99dcfd8fc827|2fcb9108|644, fees vary)", "known": "operator-A", "count": a["n"], "launches_per_day": a["launches_per_day"],
    "launcher": f"launcher 0x3194e326, 2fcb9108, 644 bytes, value 1.9-2.7 ETH, fee varies (1500/2500/3500/4000/500...), {a['n_launch_wallets']} fresh wallets (nonce 0)",
    "first_buy": (f"first non-launch buy: the dust bot at {a['fb']['off_p10_50_90']}; first real buy (the crowd, UR execute 3593564c) in {a['fr']['pools']}/{a['n']} at "
                  f"{a['fr']['off_p10_50_90']} blocks, {a['fr']['eth_p10_50_90']} ETH, {a['fr']['n_from']} wallets (0x8700722d x25, 0x295877ce x23, 0xdc2e8661 x15), none fresh"),
    "pull": (f"{a['pull']['pulled']}/{a['n']} ({100*a['pull']['frac']:.0f}%) within 3,000; from launch {a['pull']['off_launch_p10_50_90']}, from the first crowd buy "
             f"{a['pull']['off_sched_p10_50_90']}; all by the launch wallet via the POSM"),
    "outsiders": (f"{a['outsiders']['pools']}/{a['n']} pools with sub-dust outsiders before the crowd ({a['outsiders']['eth_p10_50_90']} ETH, mostly 0xf7b47b17 via UR); >= 0.0001 ETH "
                  f"in {a['trap_test']['with_outsider_ge_0.0001']['pools']}: pull {a['trap_test']['with_outsider_ge_0.0001']['pull_minus_sched_p10_50_90']} blocks after the crowd buy vs "
                  f"{a['trap_test']['without']['pull_minus_sched_p10_50_90']} without (n 2: too few)"),
    "front_rule": fmt_rule(a["front"]) + " (the crowd comes at +54, after the +20 deadline)",
    "follow_rule": fmt_rule(a["follow"]),
    "capacity": (f"UR execute is nested: not decoded; assumption minOut = 0.99 x launch-state quote: {a['capacity']['room_from_launch_p10_50_90']} ETH ahead of the first crowd buy"),
    "engine_config": "the live follow engine (launcher 0x3194e326 / 2fcb9108; trigger the first buy >= 0.0002 ETH; sell on the next buy or buy + 4)",
    "verdict": "control-known", "candidate_score": 0,
    "notes": "Matches the handoff's +2-4% follow and analyse_5's +4.34%. " + CALIB,
})
json.dump(out, open(os.path.join(HERE, "families_out.json"), "w"), indent=1)
json.dump({"families": out, "stats": S, "calibration": C, "calibration_live": {k: v for k, v in CL.items() if k != "rows"}, "trap_v2433": TR, "loose_7fde822e": LO,
           "postwindow": {k: v for k, v in PW.items() if k != "events"}}, open(os.path.join(HERE, "results.json"), "w"), indent=1, default=str)
for r in out: print(json.dumps(r, indent=1)); print()
