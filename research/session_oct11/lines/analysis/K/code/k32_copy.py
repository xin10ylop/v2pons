"""(d) copy a profitable repeat trader: on its first buy in a curve we buy after block +k; we sell after block (its first sell + k), or after
a cap. Exact curve math with our trade inserted; graduation inside the hold is valued at the migration pool after +30 blocks (census path)."""
import pickle, json, collections, sys
from kreplay import *
from kv4 import V4
P = pickle.load(open(os.path.join(DATA, "packed.pkl"), "rb")); CE = P["creates"]; TR = P["trades"]
head = json.load(open(os.path.join(DATA, "trades_head.json")))["head"]
G = {g["curve"]: g for g in json.load(open(os.path.join(OUT, "k12_grads.json"))) if g.get("curve")}
MP = {m["token"]: m for m in json.load(open(os.path.join(OUT, "k13_mig_pools.json")))}; EV = json.load(open(os.path.join(DATA, "mig_pool_events.json")))
span_days = (bts(head - 3100) - bts(79984897)) / 86400
out = {}
for w in sys.argv[1:]:
    for k in (1, 2, 5):
        for cap in (300, 3000, 30000):
            for stake in (0.002, 0.0058):
                R = []; byd = collections.defaultdict(list); ng = 0
                for c, ev in TR.items():
                    cr = CE[c]
                    if not 79984897 <= cr["bn"] <= head - 3100: continue
                    mb = [r for r in ev if r[3] == "B" and w in r[4]]
                    if not mb: continue
                    b0 = mb[0][0]; ms = [r for r in ev if r[3] == "S" and w in r[4] and r[0] > b0]
                    xb = min(ms[0][0] + k, b0 + k + cap) if ms else b0 + k + cap
                    cf = cfee(ev); cf = 0.02 if cf is None else cf
                    x = replay(ev, b0 + k, xb, stake, 0.0, cf)
                    if x is None: continue
                    if x["grad"]:
                        ng += 1; g = G.get(c); m = g and MP.get(g["token"])
                        if not m: continue
                        v = V4(m, EV[m["pool"]]); r_ = (v.sell(v.lb + 30, x["tok"], 0.01 + cf) / 1e18 - GAS_RT) / stake - 1
                    else: r_ = x["ret"]
                    R.append(r_); byd[day(cr["bn"])].append(r_)
                s = stats(R, stake, span_days); s["graduated_in_hold"] = ng; s["by_day"] = {d: [len(z), round(sum(z) / len(z), 4)] for d, z in sorted(byd.items())}
                out[f"copy {w} k={k} cap={cap} stake={stake}"] = s
                if stake == 0.0058: print(w[:10], f"k={k} cap={cap}", {z: s.get(z) for z in ("n", "mean", "median", "win", "worst", "best", "usd_per_day", "graduated_in_hold")}, s["by_day"])
json.dump(out, open(os.path.join(OUT, "k32_copy.json"), "w"), indent=1)
