"""Skeptic f2276/100 step 5: the ride (buy landing c1+d, d = 1..3, at the end of that block; sell at the head of c1+d+H) replayed exactly
on (a) the 56 fully attributed crowd pools (50 census + 6 fresh, the fresh ones out of sample) and (b) every census crowd pool (203)
with c1 from the first 8 swaps; plus the same ride at a random block (no crowd trigger: is the trigger doing anything?), and the
dollar figures at 0.0058 ETH = $15 with $0.012 gas."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_s import *
pools, TX = load_sample()
P = load_pools(); F = load_families(); T = load_txs(); pids = F[K]["pids"]; E = load_events(set(pids))
allp = []
for pid in pids:
    p = P[pid]; e = E[pid]
    sw = [dict(s, buy=s["a0"] < 0) for s in e["swaps"]]
    cr = [s for s in sw if s["tx"] in T and T[s["tx"]]["to"] == CROWD and s["buy"]]
    allp.append({"pid": pid, "b0": p["launch_block"], "ts0": p["launch_ts"], "sp0": p["sqrt_p0"], "L0": p["liq_launch"], "swaps": sw, "pulls": e["pulls"],
                 "pull_bn": e["pulls"][0]["bn"] if e["pulls"] else None, "crowd1": cr[0]["bn"] if cr else None, "src": "census"})
allp += [pl for pl in pools if pl["src"] == "fresh"]
def summ(rs, label):
    v = [r for r, why in rs if r is not None]; pulled = sum(1 for r, why in rs if why == "pulled")
    if not v: return {"label": label, "n": 0}
    s = sorted(v); m = sum(v) / len(v)
    top5 = sum(sorted(v)[-max(1, len(v) // 20):]) / len(v)
    return {"label": label, "n": len(v), "mean": round(m, 4), "median": round(s[len(s) // 2], 4), "win": round(sum(1 for x in v if x > 0) / len(v), 3),
            "pulled": pulled, "p10": round(s[len(s) // 10], 4), "p90": round(s[9 * len(s) // 10], 4), "mean_wo_top5pct": round(m - top5, 4),
            "usd_trade": round(m * 15, 3)}
out = {}
for name, group in (("attributed56", [pl for pl in pools if pl["crowd1"]]), ("census203+fresh6", [pl for pl in allp if pl["crowd1"]]),
                    ("fresh6", [pl for pl in pools if pl["src"] == "fresh"])):
    for d in (1, 2, 3):
        for H in (10, 20, 50, 100):
            rs = [replay(pl, pl["crowd1"] + d - 1 + 1 - 1 + 0 if False else pl["crowd1"] + d, pl["crowd1"] + d + H) for pl in group]
            out[f"{name}|c1+{d}|H{H}"] = summ(rs, f"{name} buy c1+{d} hold {H}")
# the trigger's value: same ride from a random block between launch+30 and launch+300 in ALL pools (crowd or not)
rnd = random.Random(7)
for H in (50,):
    rs = []
    for pl in allp:
        B = pl["b0"] + rnd.randint(30, 300); rs.append(replay(pl, B, B + H))
    out[f"random_entry|H{H}"] = summ(rs, "random entry in launch+30..300, all 251 pools")
# the no-crowd pools: what the trigger avoids (it never fires there)
for k, v in out.items(): print(k, json.dumps(v))
json.dump(out, open(os.path.join(HERE, "a5_ride.json"), "w"), indent=1)
