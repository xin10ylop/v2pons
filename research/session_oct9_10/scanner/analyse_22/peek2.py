import sys, json, collections
sys.path.insert(0, ".")
from common22 import *
K = json.load(open("keys.json"))
P = load_pools(); F = load_families(); T = load_txs(); T.update(json.load(open("extra_txs.json"))); M = load_blocks_meta()
f100 = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true"
G1 = F[K[0]]["pids"] + F[f100]["pids"]
E = load_events(set(G1))
for x in G1:
    pl = Pool(P[x], E[x], T, M)
    print("--", x[:12], "fee", P[x]["fee"], "val", P[x]["launch_value_eth"], "start", pl.start, "L0", pl.L0, "pull", (pl.pull_bn - pl.b0) if pl.pull_bn else None, "pull_from_launch_wallet", P[x]["first_pull_from"] == P[x]["launch_from"] if P[x]["first_pull_from"] else None)
    for s in pl.seq:
        tag = "CROWD" if (s["to"] == UR and s["clen"] == 1284 and s["nonce"] == 0) else ""
        print("   +%-5d %s %.6g %s %s %s len%s n%s %s" % (s["bn"] - pl.b0, "B" if s["buy"] else "S", s["eth"] / 1e18, (s["from"] or "?")[:10], (s["to"] or "?")[:10], s["sel"], s["clen"], s["nonce"], tag))
