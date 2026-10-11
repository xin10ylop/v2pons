"""Natural experiment: wallets that already buy C-1 pools after the bot's first buy (what we would do). For each repeat rider: pools,
its first post-trigger buy t, size, and the first pull within W blocks of t (observed) vs expected from the triggered pools it did not
buy in (hazard matched on dt = t - trigger). Also its realised round trips where its sell tx is fetched (same pool, sell after buy)."""
import pickle
from sim import *
rows = {r["pool"]: r for r in jl(os.path.join(V, "c1_rows.jsonl")) if r["quote"] == "ETH"}
E = pickle.load(open(os.path.join(V, "ev.pkl"), "rb")); R = pickle.load(open(os.path.join(V, "replay.pkl"), "rb"))
T = json.load(open(os.path.join(V, "c1_txs.json"))); T.update(json.load(open(os.path.join(V, "sample_txs.json"))))
crowd = {t["from"] for t in T.values() if t.get("to") == BOT}
P_ = {pid: Pool(rows[pid], E[pid]) for pid in R["trig"]}
buys = C.defaultdict(dict); sells = C.defaultdict(lambda: C.defaultdict(list))
for pid, P in P_.items():
    tb = R["trig"][pid]
    for x in P.sw:
        t = T.get(x[8])
        if t is None or t["to"] == BOT or t["from"] in crowd or t["from"] == rows[pid]["launch"]["from"]: continue
        if x[3] and x[0] >= tb[0] and pid not in buys[t["from"]]: buys[t["from"]][pid] = x
        if not x[3]: sells[t["from"]][pid].append(x)
def exp_share(ctrl, dt, W):
    alive = [c for c in ctrl if P_[c].first_pull is None or P_[c].first_pull > R["trig"][c][0] + dt]
    return sum(1 for c in alive if P_[c].first_pull is not None and P_[c].first_pull <= R["trig"][c][0] + dt + W) / len(alive) if alive else 0
out = {}
for w, bp in sorted(buys.items(), key=lambda kv: -len(kv[1])):
    if len(bp) < 10: continue
    ctrl = [p for p in P_ if p not in bp]
    dts = [x[0] - R["trig"][p][0] for p, x in bp.items()]; sz = [x[4] / 1e18 for x in bp.values()]
    line = f"{w} pools {len(bp)} buy at trig+ p10/50/90 {p3(dts)} size med {pct(sz, 0.5):.5f}"
    res = {}
    for W in (30, 60, 100):
        obs = sum(1 for p, x in bp.items() if P_[p].first_pull is not None and x[0] <= P_[p].first_pull <= x[0] + W)
        ex = sum(exp_share(ctrl, x[0] - R["trig"][p][0], W) for p, x in bp.items())
        res[W] = (obs, round(ex, 1)); line += f" | pulled within {W} of its buy {obs} vs exp {ex:.1f}"
    # realised round trips (sell tx fetched, after its buy)
    rt = []
    for p, x in bp.items():
        s = [y for y in sells[w].get(p, []) if y[0] >= x[0]]
        if s:
            y = s[0]; rt.append(((y[4] - x[4]) / x[4], y[0] - x[0]))
    if rt: line += f" | round trips seen {len(rt)}: return mean {sum(a for a, _ in rt)/len(rt):+.3f} med {pct([a for a, _ in rt], 0.5):+.3f}, held p10/50/90 {p3([b for _, b in rt])}"
    print(line); out[w] = {"n": len(bp), "dts": dts, "res": res, "rt": rt}
json.dump(out, open(os.path.join(V, "v12_rider_reaction.json"), "w"))
