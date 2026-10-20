"""The 0x0000ffff 1.5-ETH dev-buy operator: the assigned 3236-byte family plus its 3204-byte sibling (same launcher, same value, same R75
buy). Entry-time variants around the R75 buy (minOut 0, decoded) and the launcher's dumps."""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import analyse as A
from common13 import *  # noqa
F = A.F; P = A.P
k3236 = A.KEYS[2]
k3204 = [k for k in F if k.startswith("0x0000ffffbe8efe702c8703ae3477ff5de3d319c0|ac9650d8|3204|")][0]
E = load_events(set(F[k3236]["pids"]) | set(F[k3204]["pids"]))
out = {"k3204": k3204, "pools": [], "variants": {}}
pools = []
for k in (k3236, k3204):
    for pid in F[k]["pids"]:
        pool = Pool(P[pid], E.get(pid), A.T, A.M); pools.append((k, pid, pool))
        if k == k3204:
            A.E[pid] = E[pid]
            r = A.pool_row(pid, "r75")
            out["pools"].append({x: r[x] for x in ("pid", "b0", "launch_from", "nonce", "value", "buy_in_launch_tx", "sched", "launcher_sells", "front", "front_wait", "follow", "cap")})
            print("3204", pid[:10], "sched", r["sched"] and (r["sched"]["rel"], r["sched"]["eth"]), "lsells", r["launcher_sells"], "front", round(r["front"]["ret"], 4), "wait", round(r["front_wait"]["ret"], 4),
                  "follow", r["follow"] and round(r["follow"]["ret"], 4), "buys", [(b[0], b[1]) for b in r["buys40"][:8]])

def sched_of(pool):
    return next((x for x in pool.buys() if x["to"] == R75), None)

def run(entry, cap, fams):
    rs = []
    for k, pid, pool in pools:
        if k not in fams: continue
        sb = sched_of(pool); B = pool.b0 + entry
        if sb is not None and sb["bn"] <= B:
            rs.append({"exit": "sched_before_our_buy", "ret": None}); continue
        S = min(sb["bn"] + 1, pool.b0 + cap) if sb else pool.b0 + cap
        r = pool.trade(B, S); r["pid"] = pid[:10]; rs.append(r)
    return rs

for fams, lab in (((k3236,), "3236"), ((k3236, k3204), "3236+3204")):
    for entry in (1, 20, 60, 100, 120):
        for cap in (20, 300, 3000):
            if cap <= entry: continue
            rs = run(entry, cap, fams); s = summarize(rs)
            s["per_pool"] = [(r.get("pid"), r["exit"], r["ret"] and round(r["ret"], 4), r.get("S")) for r in rs]
            out["variants"][f"{lab}|buy+{entry}|sell sched+1 cap +{cap}"] = s
            print(f"{lab:10s} buy +{entry:3d} cap +{cap:4d}: {fmt_rule(s)} | {[(r['ret'] and round(r['ret'],3)) for r in rs]}")
json.dump(out, open(os.path.join(HERE, "fam3_variants.json"), "w"), indent=1, default=str)
