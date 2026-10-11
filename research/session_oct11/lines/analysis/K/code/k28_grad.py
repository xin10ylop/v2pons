"""Q3(b) buy on the curve once its real ETH crosses a level, exit in the v4 pool after the migration (or on the curve if it does not graduate
in time); Q3(c) buy in the migration pool at migration + 1/2 blocks, sell at + H. Exact curve math; v4 full-range math with the hook's fee
(1% + the curve's creator fee) on each output; gas. By day."""
import pickle, json, collections
from kreplay import *
from kv4 import V4
P = pickle.load(open(os.path.join(DATA, "packed.pkl"), "rb")); CE = P["creates"]; TR = P["trades"]
head = json.load(open(os.path.join(DATA, "trades_head.json")))["head"]
G = {g["curve"]: g for g in json.load(open(os.path.join(OUT, "k12_grads.json"))) if g.get("curve")}
MP = {m["token"]: m for m in json.load(open(os.path.join(OUT, "k13_mig_pools.json")))}
EV = json.load(open(os.path.join(DATA, "mig_pool_events.json")))
span_days = (bts(head - 3100) - bts(79984897)) / 86400
V = {}
for c, g in G.items():
    m = MP.get(g["token"])
    if m and c in CE: V[c] = (g, V4(m, EV[m["pool"]]))
print("graduated window curves with a v4 path", len(V), "full-range-only", sum(1 for g, v in V.values() if v.full_range_only))
out = {}
# ---------- (c) the migration pool
for k in (1, 2):
    for H in (5, 10, 30, 100, 300, 1000, 2900):
        for stake in (0.002, 0.0058):
            R = []; byd = collections.defaultdict(list)
            for c, (g, v) in V.items():
                cf = cfee(TR.get(c, [])) or 0.0; fee = 0.01 + cf
                e = v.lb + k; x = e + H
                tok = v.buy(e, stake * 1e18, fee); eth = v.sell(x, tok, fee) / 1e18
                r = (eth - GAS_RT) / stake - 1; R.append(r); byd[day(v.lb)].append(r)
            s = stats(R, stake, span_days); s["by_day"] = {d: [len(z), round(sum(z) / len(z), 4)] for d, z in sorted(byd.items())}
            out[f"(c) v4 entry mig+{k} hold {H} stake {stake}"] = s
            if stake == 0.0058: print(f"(c) mig+{k} H={H}", {z: s[z] for z in ("n", "mean", "median", "win", "worst", "best", "usd_per_day")})
# ---------- (b) the curve before graduation
def first_cross(ev, L):
    cv = Curve()
    for r in ev:
        if cv.apply(r) and cv.real() >= L * 1e18: return r[0]
    return None
crosses = {}
for L in (1.0, 2.0, 3.0, 3.5, 3.9):
    crosses[L] = {c: b for c in CE if 79984897 <= CE[c]["bn"] <= head - 3100 for b in [first_cross(TR.get(c, []), L)] if b}
    print("curves whose real ETH crossed", L, len(crosses[L]), "of which graduated", sum(1 for c in crosses[L] if c in G))
for L in (1.0, 2.0, 3.0, 3.5, 3.9):
    for W in (300, 3000, 30000):
        for h in (2, 30, 300):
            if W != 3000 and h != 30: continue
            for stake in (0.002, 0.0058):
                R = []; byd = collections.defaultdict(list); ng = nm = 0
                for c, tb in crosses[L].items():
                    ev = TR.get(c, []); cf = cfee(ev); cf = 0.02 if cf is None else cf
                    x = replay(ev, tb + 2, tb + 2 + W, stake, 0.0, cf)
                    if x is None: nm += 1; continue          # graduated before our entry
                    if x["grad"]:
                        ng += 1
                        if c not in V: continue
                        g, v = V[c]
                        if not v.full_range_only and False: pass
                        eth = v.sell(v.lb + h, x["tok"], 0.01 + cf) / 1e18
                        r = (eth - GAS_RT) / stake - 1
                    else: r = x["ret"]
                    R.append(r); byd[day(CE[c]["bn"])].append(r)
                s = stats(R, stake, span_days); s.update({"graduated_in_hold": ng, "missed_graduated_before_entry": nm, "by_day": {d: [len(z), round(sum(z) / len(z), 4)] for d, z in sorted(byd.items())}})
                out[f"(b) cross {L} ETH, entry +2, window {W}, v4 exit mig+{h}, stake {stake}"] = s
                if stake == 0.0058: print(f"(b) L={L} W={W} h={h}", {z: s.get(z) for z in ("n", "mean", "median", "win", "worst", "best", "usd_per_day", "graduated_in_hold", "missed_graduated_before_entry")})
json.dump(out, open(os.path.join(OUT, "k28_grad.json"), "w"), indent=1)
