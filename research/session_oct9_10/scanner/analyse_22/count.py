import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
K = json.load(open("keys.json"))
P = load_pools(); F = load_families(); T = load_txs()
f100 = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true"
print(F[f100]["count"], F[f100]["values_eth"], F[f100]["known"], F[f100]["n_deployers"])
for x in F[f100]["pids"]:
    p = P[x]; print(x[:12], p["launch_value_eth"], p["launch_from"][:10], p["launch_nonce"], p["liq_launch"], p["tick0"], p["n_buys"], p["first_pull_rel"], p["first_pull_from"] == p["launch_from"] if p["first_pull_from"] else None)
G1 = F[K[0]]["pids"] + F[f100]["pids"]; G3 = F[K[2]]["pids"]
E = load_events(set(G1 + G3))
miss1 = set(s["tx"] for x in G1 for s in E[x]["swaps"] if s["tx"] not in T)
miss3 = set(s["tx"] for x in G3 for s in E[x]["swaps"][:80] if s["tx"] not in T)
print("missing txs G1", len(miss1), "G3 (first 80 swaps)", len(miss3))
