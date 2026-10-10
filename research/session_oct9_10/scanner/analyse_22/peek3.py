import sys, json, collections
sys.path.insert(0, ".")
from common22 import *
K = json.load(open("keys.json"))
P = load_pools(); F = load_families(); T = load_txs(); T.update(json.load(open("extra_txs.json"))); M = load_blocks_meta()
G3 = F[K[2]]["pids"]
E = load_events(set(G3))
cnt = collections.Counter()
for x in G3:
    pl = Pool(P[x], E[x], T, M)
    print("--", x[:12], "fee", P[x]["fee"], "start", pl.start, "L0", pl.L0, "s_eff", pl.s_eff, "pull", (pl.pull_bn - pl.b0) if pl.pull_bn else None, "adds", [(a["bn"] - pl.b0, a["lo"], a["hi"], a["dl"]) for a in pl.adds])
    for s in pl.seq[:60]:
        cnt[(s["to"], s["sel"])] += 1
        print("   +%-5d ti%-3d %s %.6g %s %s %s len%s n%s fee%s liq%s" % (s["bn"] - pl.b0, s["ti"], "B" if s["buy"] else "S", s["eth"] / 1e18, (s["from"] or "?")[:10], (s["to"] or "?")[:10], s["sel"], s["clen"], s["nonce"], s["fee"], s["liq"]))
print(cnt.most_common())
