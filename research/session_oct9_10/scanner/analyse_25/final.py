"""analyse_25 final: assembles families_out.json (the structured answer) from results.json (analyse.py), extra.json, dump_model.json and
dumper_link.json."""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "results.json"))); X = json.load(open(os.path.join(HERE, "extra.json")))
DM = json.load(open(os.path.join(HERE, "dump_model.json"))); DL = json.load(open(os.path.join(HERE, "dumper_link.json")))
K = json.load(open(os.path.join(HERE, "keys.json")))
def fr(s):
    if not s or not s.get("n"): return "n 0"
    return (f"n {s['n']}, mean {100*s['mean']:+.2f}%, median {100*s['median']:+.2f}%, win {100*s['win']:.0f}%, pulled-first {s['pulled_first']}, "
            f"${s['usd_trade']:+.3f} a trade, ${s['usd_day']:+.2f} a day ({s['trades_day']} trades/day)")
g = lambda pfx: next(v for k, v in R.items() if k.startswith(pfx))
F1, F2, F3, F4 = (R["F%d %s" % (i + 1, k)] for i, k in enumerate(K))
L_CE, L_D1, DEP, WIDE, L_E1 = g("F1-LAUNCHER"), g("F2F3-LAUNCHER"), g("DEP-0x06cb3a68"), g("WIDE-7fde822e"), g("F4-LAUNCHER")
C = R["controls"]; V = R["CONTROL vbot-v2.433"]; A = R["CONTROL operator-A"]
dump_after = DM["sell_after_dump ratio 0.980"]["ret"]; dump_before = DM["sell_before_dump (launch+2)"]["ret"]
pairs = DM["dump_pairs"]
d06 = X["0x06cb3a6841c92525e7a1998328e7c9d37e98d937"]; d84 = X["0x843784a6d2c839ca170e64c75dcc797dfc4a86a3"]
calib = (f"Pricer analyse_25/common25.py (analyse_23/common23.py verbatim, the replay of explore/chk/replay.py) re-calibrated here: vbot-v2.433 front sold one block "
         f"after the bot's buy {fr(C['v2433_front_bot_sched_all'])} (median +14.01%); live window Oct 10 09:07-11:39 {fr(C['v2433_front_livewindow_oct10_0907_1139'])}; "
         f"our 1,080 real relay round trips re-priced: model mean 8.705% vs real 8.736%, median abs diff 3e-16. In-family check: every buy in the assigned groups "
         f"(498 swaps) re-priced from the model state to within 3e-16 of its Swap event.")
DUMP = (f"The class's own trap (not a pull): each 7fde822e launch mints 25% of the token (250M of 1B) straight to wallet 0x94dddbb5, named in calldata word 7 "
        f"(478 of 490 class launches, all 454 of 0x06cb3a68's; dumper_link.json); the other 750M go into a TOKEN-ONLY position (range 132800..201800, price at its "
        f"upper edge tick 201800, 0 ETH), so the pool's only ETH is what buyers bring. 0x94dddbb5 sold into every one of the class's 5 real buys (0.0012-0.0107 ETH) "
        f"{sorted(p['delay'] for p in pairs)} blocks later, taking back {min(p['ratio'] for p in pairs):.3f}-{max(p['ratio'] for p in pairs):.3f} of the buyer's ETH. "
        f"Priced on our 0.0058 ETH buy with the range edge enforced (dump_model.py): sold before the dump (launch+2) {100*dump_before:+.2f}%, sold after it {100*dump_after:+.2f}% "
        f"(the replay above cannot show this: it moves the dumper's sell by its own observed price shift, sized to the original buyer, not to us).")
WIDECLASS = (f"Deployer 0x06cb3a68 used 23 launch contracts in the window (19,028-19,038 bytes), exactly 20 launches each (one at 14 when the window closed), each batch about 1.5 h, 12 launches an hour around the clock: {DEP['count']} pools in "
             f"the 48 h window ({DEP['launches_per_day']}/day), still launching after it (nonce {d06['nonce_last_launch_in_window']} at its last census launch, {d06['nonce_now']} at "
             f"{d06['head_utc']} UTC). The strict families split one contract's batch by calldata length (740/772/804/836 = token name/symbol length). Whole deployer: real buys "
             f"(>= 0.0002) in {DEP['first_buy_real']['pools_with']}/454 pools at +3..+1625 by 5 unrelated wallets via 5 routers, 0 pulls; front {fr(DEP['front'])}; follow {fr(DEP['follow'])}. "
             f"Whole 7fde822e class (490 pools, 5 deployers): front {fr(WIDE['front'])}. Token names copy other projects (TRACE/gettrace.pro, Cirrascend, LOL/lolonhood.com; "
             f"images at imortal.buzz).")
out = []
for key, f, lc, lname, nb in ((K[0], F1, L_CE, "0xce4c6a28 (19,038 bytes)", "nonces 2050-2064, Oct 09 13:11-14:21 UTC"),
                              (K[1], F2, L_D1, "0xd1e3060e (19,032 bytes)", "nonces 1963-1982, Oct 09 04:23-05:57 UTC"),
                              (K[2], F3, L_D1, "0xd1e3060e (19,032 bytes)", "nonces 1968-1979, Oct 09 04:47-05:42 UTC")):
    lens = sorted(int(x[0].split(":")[2]) for x in lc["launch_to_sel_len"])
    out.append({
        "key": key, "known": "none", "count": f["count"], "launches_per_day": f["launches_per_day"],
        "launcher": (f"Launch contract {lname}, selector 7fde822e, {key.split('|')[2]} bytes, value 0; one deployer 0x06cb3a68 ({nb}). The call creates a 1B-supply token, mints "
                     f"750M into a token-only position (132800..201800, tick0 201800 = its upper edge, L 3.2156e22, 0 ETH) at fee 1%, tick spacing 200, no hook, and sends 250M "
                     f"to 0x94dddbb5. The launch contract made {lc['count']} launches in all ({lens} bytes), all by 0x06cb3a68."),
        "first_buy": (f"No non-launch buy of >= 0.0002 ETH in any pool (0/{f['count']}; 0/{lc['count']} for the launch contract). The only buy, in {f['first_buy_any']['pools_with']}/{f['count']} "
                      f"pools, is the chain-wide dust bot 0xe71a69f4 (1 wallet, nonces 92k+): 2e-6 ETH through the Universal Router (3593564c, 1,156 bytes) at offset p10/50/90 "
                      f"{f['first_buy_any']['off_p10_50_90']} blocks. No sells. No schedule, no operator buy."),
        "pull": (f"0/{f['count']} pulled within 3,000 blocks (0/454 for the deployer, 0/490 for the class). There is nothing to pull: the position holds no ETH."),
        "outsiders": (f"No outsider buy besides the dust bot (excluded); with no pull at all the pull-delay trap test is empty (with outsider 0/0, without 0/{f['count']} pulled). "
                      + DUMP),
        "front_rule": (f"{fr(f['front'])}. No scheduled buy ever came, so every trade sold at launch+20 into an untouched pool: two 1% fees plus gas ($0.011). "
                       f"Without the 20-block cap: {fr(f['front_no20cap (sell 1 block after the first real buy, deadline +3000)'])}. With the dump wallet reacting to our buy, "
                       f"a sell after its dump returns {100*dump_after:+.2f}% (dump_model.py)."),
        "follow_rule": f"n 0: no buy of >= 0.0002 ETH, so no trigger. (Deployer-wide: {fr(DEP['follow'])}; the dumper's sells are replayed by their observed shift, so the real result would be worse.)",
        "capacity": "n/a: there is no scheduled buy to sit ahead of.",
        "engine_config": ("Not worth trading. Recognizer if wanted for exclusion: to = one of 0x06cb3a68's launch contracts, selector 7fde822e, value 0, calldata 740-964 bytes with "
                          "0x94dddbb5 in word 7; fee 10000, tick spacing 200, hooks 0, token-only range at tick 201800. Eligibility must reject it: 0 ETH in the pool and a 25%-supply "
                          "dump wallet."),
        "verdict": "no-schedule", "candidate_score": 0,
        "notes": WIDECLASS + " " + calib,
    })
out.append({
    "key": K[3], "known": "none", "count": F4["count"], "launches_per_day": F4["launches_per_day"],
    "launcher": (f"Launch contract 0xe181b36e (23,627 bytes), selector a25a9a3d, 900 bytes, value 0.000100683 ETH (100,683,270,263,326 wei, the same in all 16 of its launches); "
                 f"one deployer 0x843784a6 (nonces 28-41). The call mints a 1B token, sends 200M (20%) to the deployer and 800M into a position 87200..207200 at tick 207199 "
                 f"(L 2.5417e22, holding 4.0e-5 ETH), fee 1%, tick spacing 200, no hook. 0xe181b36e made 16 launches in all (804/868/900 bytes), all by 0x843784a6, all in 75 "
                 f"minutes (Oct 08 21:52-23:08 UTC); the deployer has sent one transaction since (nonce {d84['nonce_last_launch_in_window']} -> {d84['nonce_now']} at {d84['head_utc']} UTC; "
                 f"balance {d84['balance_eth_now']:.6f} ETH). Token metadata impersonates Robinhood (name Robinhood/ROBINHOOD, rhonrobinhood.com, x.com/rhonrobinhood, "
                 f"t.me/robinhood_com, metadata at cronos.hypercarsbrokers.xyz)."),
    "first_buy": (f"No buy of >= 0.0002 ETH in any pool (0/5; 0/16 for the launcher). The only buy in {F4['first_buy_any']['pools_with']}/5 pools is the dust bot 0xe71a69f4: 2e-6 ETH via the "
                  f"Universal Router at offset p10/50/90 {F4['first_buy_any']['off_p10_50_90']}. No sells."),
    "pull": "0/5 pulled within 3,000 blocks (0/16 for the launcher). The position holds 4e-5 ETH; the deployer never touched it in the window.",
    "outsiders": "None besides the dust bot (excluded). No pulls with or without, so the trap test is empty. The deployer keeps 20% of supply off-pool, the same dump set-up as the 7fde822e class, but no real buy ever came to show a dump.",
    "front_rule": (f"{fr(F4['front'])}. All sold at launch+20 with no scheduled buy: two 1% fees plus gas ($0.012). Launcher-wide (16): {fr(L_E1['front'])}."),
    "follow_rule": "n 0: no buy of >= 0.0002 ETH, so no trigger (0/16 launcher-wide).",
    "capacity": "n/a: no scheduled buy.",
    "engine_config": "Not worth trading. Recognizer: to 0xe181b36e, a25a9a3d, value 100683270263326 wei, from 0x843784a6; fee 10000, ts 200, hooks 0. Dormant since Oct 08 23:08 UTC.",
    "verdict": "no-schedule", "candidate_score": 0,
    "notes": "A one-evening burst of 16 Robinhood-impersonation tokens by one wallet; only the dust bot touched them. " + calib,
})
out.append({
    "key": "CONTROL vbot-v2.433: 0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true at 2.4333285 ETH", "known": "vbot-v2.433", "count": V["count"],
    "launches_per_day": V["launches_per_day"],
    "launcher": "POSM multicall ac9650d8, 1,444 bytes, exactly 2.4333285 ETH, fee 2500, ts 50, full range, L 4.93e22; a fresh wallet per launch (1843 deployers).",
    "first_buy": (f"The bot's router buy (0x1cbaf24d c1120e3d) in {V['bot_buy']['pools_with']}/1843 pools, offset p10/50/90 {V['bot_buy']['off_p10_50_90']}, size {V['bot_buy']['eth_p10_50_90']} ETH, "
                  f"{V['bot_buy']['n_from']} wallets; minOut / launch-state quote {V['bot_buy']['minout_over_launch_quote_p10_50_90']}."),
    "pull": (f"{100*V['pull']['frac']:.1f}% pulled within 3,000 blocks, from launch {V['pull']['off_launch_p10_50_90']}, from the bot's buy {V['bot_buy']['pull_minus_bot_buy_p10_50_90']} "
             f"(3 blocks in 1044 pools), all by the launch wallet via 0x1cbaf24d a0f7978d."),
    "outsiders": f"607 pools had buys by others before the first real buy, nearly all the operator's decoys (~0.00012 ETH); pull after them {V['trap']['delay_after_outsider_p10_50_90']} vs {V['trap']['pull_off_without_p10_50_90']} from launch without.",
    "front_rule": f"Sold one block after the bot's buy (else +20): {fr(C['v2433_front_bot_sched_all'])}; live window {fr(C['v2433_front_livewindow_oct10_0907_1139'])}. Generic schedule (first buy >= 0.0002): {fr(V['front'])}.",
    "follow_rule": fr(V["follow"]) + ": the pull 3 blocks after the bot's buy beats a follow exit.",
    "capacity": f"minOut decoded from calldata word 4 (= 0.99 x launch quote); ETH that fits ahead of the bot's buy p10/50/90 {C['v2433_capacity_p10_50_90']}.",
    "engine_config": "Live: front (HANDOFF 3.2).", "verdict": "control-known", "candidate_score": 0,
    "notes": "Calibration control: median +14.01% reproduces the live ~+14%. " + calib,
})
out.append({
    "key": "CONTROL operator-A: launcher 0x3194e32622c5d860a0572c74edda99dcfd8fc827, 2fcb9108, 644 bytes", "known": "operator-A", "count": A["count"], "launches_per_day": A["launches_per_day"],
    "launcher": "To 0x3194e326, 2fcb9108, 644 bytes, value 1.7-3.16 ETH, fee varies, a fresh wallet per launch (nonce 0).",
    "first_buy": f"First real buy in 75/77 pools at offset {A['first_buy_real']['off_p10_50_90']}, size {A['first_buy_real']['eth_p10_50_90']} ETH, Universal Router 1,124-byte execute, 10 crowd wallets.",
    "pull": f"{100*A['pull']['frac']:.1f}% pulled within 3,000 blocks, from launch {A['pull']['off_launch_p10_50_90']}, from the first real buy {A['pull']['off_from_first_real_buy_p10_50_90']}, by the launch wallet via POSM dd46508f.",
    "outsiders": f"29 pools with small outsider buys (mostly 0xf7b47b17, 6e-5 ETH); pull after them {A['trap']['delay_after_outsider_p10_50_90']} vs {A['trap']['pull_off_without_p10_50_90']} from launch without.",
    "front_rule": f"{fr(A['front'])} (the 20-block cap sells before the crowd at +54); no cap: {fr(A['front_no20cap (sell 1 block after the first real buy, deadline +3000)'])}.",
    "follow_rule": fr(A["follow"]) + " (live follow: +2-4%).",
    "capacity": f"UR execute not decoded: ASSUMED minOut = 0.99 x launch quote, room {A['capacity']['cap_eth_p10_50_90']} ETH.",
    "engine_config": "Live: follow (HANDOFF 3.1).", "verdict": "control-known", "candidate_score": 0, "notes": "",
})
json.dump({"families": out}, open(os.path.join(HERE, "families_out.json"), "w"), indent=1)
print(json.dumps({"families": out}, indent=1))
