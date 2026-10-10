"""follow variants on the 1.5-ETH operator (3236 + 3204): buy one block after the first R75 buy, sell one block after the next buy of
>= X ETH or at buy + H"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common13 import *  # noqa
P = load_pools(); F = load_families(); T = load_txs(); M = load_blocks_meta()
keys = [k for k in F if k.startswith("0x0000ffffbe8efe702c8703ae3477ff5de3d319c0|ac9650d8|3236|") or k.startswith("0x0000ffffbe8efe702c8703ae3477ff5de3d319c0|ac9650d8|3204|")]
pids = [p for k in keys for p in F[k]["pids"]]
E = load_events(set(pids))
pools = [Pool(P[p], E.get(p), T, M) for p in pids]
out = {}
for X in (0.0002, 0.01, 0.05, 0.1):
    for H in (4, 20, 50, 100, 200):
        rs = []
        for pool in pools:
            buys = pool.buys(); sb = next((x for x in buys if x["to"] == R75), None)
            if sb is None: continue
            B = sb["bn"] + 1
            nxt = next((x for x in buys if x["bn"] > B and x["eth"] >= int(X * 1e18)), None)
            S = min(nxt["bn"] + 1, B + H) if nxt else B + H
            r = pool.trade(B, S); rs.append(r)
        s = summarize(rs); s["rets"] = [round(r["ret"], 4) for r in rs if r["ret"] is not None]
        out[f"next>={X}|H{H}"] = s
        print(f"next >= {X:6} H {H:3d}: {fmt_rule(s)} {s['rets']}")
json.dump(out, open(os.path.join(HERE, "fam3_follow.json"), "w"), indent=1)
