"""Reaction to a stranger buying right after the bot's first buy (what our trade looks like to the operator).
Stranger = a buy whose tx did not go to the bot's router, whose sender is not the launch wallet, not one of the bot's EOAs (every EOA
seen calling 0xd6d35b56 in any fetched tx) and not ours. Every swap in [trigger, trigger+100] of all 573 triggered pools is attributed
(census txs + v09/v13 fetch). The stranger window K (default 10) is the first argument. Stranger pool: a stranger buy >= X ETH in (trigger tx, trigger + 10]; t = its block. Outcome: the first pull in
[t, t + W] (after the buy). Control: triggered pools with no stranger buy >= 0.0001 ETH in that window; expected = sum over stranger pools of
the share of control pools still unpulled at trigger + dt whose first pull falls in (trigger + dt, trigger + dt + W] (dt = t - trigger).
Then the analysts' two census definitions (A: outsider12 nf reaction <= 30 blocks; B: outsider12 any, pull within 100) reproduced."""
import pickle
from sim import *
K = int(sys.argv[1]) if len(sys.argv) > 1 else 10
rows = {r["pool"]: r for r in jl(os.path.join(V, "c1_rows.jsonl")) if r["quote"] == "ETH"}
E = pickle.load(open(os.path.join(V, "ev.pkl"), "rb")); R = pickle.load(open(os.path.join(V, "replay.pkl"), "rb"))
T = json.load(open(os.path.join(V, "c1_txs.json"))); T.update(json.load(open(os.path.join(V, "sample_txs.json"))))
crowd = {t["from"] for t in T.values() if t.get("to") == BOT}
print(f"bot EOAs (seen calling the router): {len(crowd)}")
P_ = {pid: Pool(rows[pid], E[pid]) for pid in R["trig"]}
def pull_pos(P):
    return min(((p["bn"], p["li"]) for p in P.pulls), default=None)
info = {}
for pid, tb in R["trig"].items():
    P = P_[pid]; r = rows[pid]; L = r["launch"]["from"]; st = []; unatt = 0
    for x in P.sw:
        if not (tb[0] <= x[0] <= tb[0] + K and (x[0], x[2]) > (tb[0], tb[2]) and x[3]): continue
        t = T.get(x[8])
        if t is None: unatt += 1; continue
        if t["to"] == BOT or t["from"] == L or t["from"] in crowd or t["from"] in OURS: continue
        st.append((x[0], x[2], x[4] / 1e18, t["from"], f"{t['to'][:10]}:{t['selector']}:{t['calldata_len']}", x[8]))
    info[pid] = {"st": st, "unatt": unatt, "pp": pull_pos(P), "T": tb[0], "lb": P.lb}
print("unattributed buys in the window:", sum(v["unatt"] for v in info.values()))
ctrl = [pid for pid, v in info.items() if not any(s[2] >= 0.0001 for s in v["st"])]
def expected(dt, W):
    alive = [c for c in ctrl if info[c]["pp"] is None or info[c]["pp"][0] > info[c]["T"] + dt]
    if not alive: return 0.0
    return sum(1 for c in alive if info[c]["pp"] is not None and info[c]["pp"][0] <= info[c]["T"] + dt + W) / len(alive)
out = {"crowd_n": len(crowd), "rows": {}}
print(f"control pools (no stranger buy >= 0.0001 in the window): {len(ctrl)}")
for X in (0.0001, 0.001, 0.005):
    for W in (10, 30, 60, 100):
        sp = []
        for pid, v in info.items():
            ss = [s for s in v["st"] if s[2] >= X]
            if ss: sp.append((pid, ss[0]))
        obs = 0; exp = 0.0
        for pid, s in sp:
            pp = info[pid]["pp"]
            obs += pp is not None and pp > (s[0], s[1]) and pp[0] <= s[0] + W
            exp += expected(s[0] - info[pid]["T"], W)
        print(f"stranger >= {X:<6} ETH, pull within {W:3d} blocks of its buy: {obs}/{len(sp)} observed vs {exp:.1f} expected from controls")
        out["rows"][f"{X}|{W}"] = (len(sp), obs, round(exp, 2))
# list: stranger >= 0.001, any pull within 100 blocks, with timings
print(f"\nstranger pools (>= 0.001 ETH within {K} blocks of the trigger): every one pulled within 100 blocks of the stranger buy")
lst = []
for pid, v in info.items():
    ss = [s for s in v["st"] if s[2] >= 0.001]
    if not ss: continue
    s = ss[0]; pp = v["pp"]
    d = (pp[0] - s[0]) if pp else None
    lst.append((pid, s, d))
    if d is not None and d <= 100:
        print(f"  {pid[:12]} launch {rows[pid]['launch_utc']} trig +{v['T']-v['lb']} stranger +{s[0]-v['lb']} (trig+{s[0]-v['T']}) {s[2]:.5f} ETH {s[3][:10]} {s[4]} | pull +{pp[0]-v['lb']} = stranger+{d}, our trig+2/H60 sell at trig+62 -> pull - sell = {pp[0]-(v['T']+62)}")
print(f"stranger pools: {len(lst)}; strangers' fingerprints: {C.Counter(s[4] for _, s, _ in lst).most_common(8)}; wallets: {C.Counter(s[3][:10] for _, s, _ in lst).most_common(6)}")
# pull delay after the trigger: stranger pools vs control
for name, group in (("stranger>=0.001", [pid for pid, _, _ in lst]), ("control", ctrl)):
    d = [info[p]["pp"][0] - info[p]["T"] for p in group if info[p]["pp"]]
    print(f"{name}: n {len(group)} pulled in window {len(d)} ({len(d)/len(group):.0%}); pull - trigger p10/50/90 {p3(d)}; pulled by trig+62: {sum(1 for x in d if x <= 62)} ({sum(1 for x in d if x <= 62)/len(group):.1%}); by trig+100: {sum(1 for x in d if x <= 100)/len(group):.1%}")
# the analysts' census definitions
allr = [r for r in rows.values() if r["ev_complete"]]
a_n = [r for r in allr if r["outsider12"].get("nf_n")]; a_b = [r for r in allr if r["outsider12"]["n"] == 0 and r["outsider12"]["n_buys12_before_pull"] > 0]
print(f"\nA's definition (census outsider12 nf reaction: pull <= 30 blocks after the last no-shared-fp outsider buy in the first 12 swaps): "
      f"{sum(1 for r in a_n if r['outsider12'].get('nf_reaction'))}/{len(a_n)} vs baseline {sum(1 for r in a_b if r.get('pull_after_last_buy12') is not None and r['pull_after_last_buy12'] <= 30)}/{len(a_b)}")
o12 = [r for r in allr if r["outsider12"].get("n")]
print(f"B's definition (outsider12 any, pull within 100 of the last outsider buy in the first 12 swaps): {sum(1 for r in o12 if r['first_pull_off'] is not None and r['outsider12']['last_off'] < r['first_pull_off'] <= r['outsider12']['last_off'] + 100)}/{len(o12)}")
print("  those cases:")
for r in o12:
    lo = r["outsider12"]["last_off"]; fp = r["first_pull_off"]
    if fp is not None and lo < fp <= lo + 100:
        tb = R["trig"].get(r["pool"]); tr = (tb[0] - r["launch_block"]) if tb else None
        print(f"   {r['pool'][:12]} {r['launch_utc']} outsider +{lo} {r['outsider12']['last_eth']} fp {r['outsider12']['last_fp'][:40]} | bot trigger +{tr} | pull +{fp} (outsider+{fp-lo}; trigger+{fp-tr if tr is not None else None})")
json.dump({"out": out, "list": [(p, s, d) for p, s, d in lst]}, open(os.path.join(V, f"v10_reaction_K{K}.json"), "w"))
