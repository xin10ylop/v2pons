import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families(); P = load_pools(); T = load_txs()
k = "0xfcd182416ca91a9e88e9fe44e4f78ea3cb2c15c7|6fe958d8|68|100000|200|false"
pids = F[k]["pids"]
E = load_events(pids)
for pid in pids[:6] + pids[-2:]:
    p = P[pid]; e = E[pid]; b0 = p["launch_block"]
    print("=" * 80); print(pid, b0, "sqrt_p0", p["sqrt_p0"], "tick0", p["tick0"])
    lt = T[p["launch_tx"]]; print(" launch tx", lt["hash"], lt["from"], lt["to"], lt["selector"], lt.get("input"))
    for a in e["adds"]: print(" add", a["bn"] - b0, a["ti"], a["li"], a["lo"], a["hi"], a["dl"], a["sender"][:10], a["tx"][:12], a["tx"] == p["launch_tx"])
    for a in e["pulls"]: print(" pull", a["bn"] - b0, a["ti"], a["li"], a["lo"], a["hi"], a["dl"], a["sender"][:10], a["tx"][:12])
    for s in e["swaps"]:
        t = T.get(s["tx"])
        print(" swap", s["bn"] - b0, s["a0"], s["a1"], s["sqrt_p"], s["liq"], s["tick"], s["fee"], s["sender"][:10], t and (t["from"], t["to"], t["selector"], t["value_eth"], t["calldata_len"]))
    for z in e["zero_mods"]: print(" zero", z["bn"] - b0, z["sender"][:10])
    for h in set([x["tx"] for x in e["pulls"]]):
        t = T.get(h)
        if t: print(" pulltx", t["from"], t["to"], t["selector"], t.get("input"))
