import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families(); P = load_pools(); T = load_txs()
for k, nshow in (("0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|838974|9303|true", 5),
          ("0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|3000|60|true", 18),
          ("0x815542e8b392389a1389e22e588e4b62a67ade72|7c33638d|769|30000|200|true", 4)):
    pids = F[k]["pids"]
    E = load_events(pids)
    print("#" * 100); print(k)
    for pid in pids[:nshow] + [x for x in pids if P[x]["n_swaps"] and x not in pids[:nshow]]:
        p = P[pid]; e = E[pid]; b0 = p["launch_block"]
        print("=" * 80); print(pid, b0, "sqrt_p0", p["sqrt_p0"], "tick0", p["tick0"], "token", p["token"])
        lt = T[p["launch_tx"]]; print(" launch tx", lt["hash"][:14], lt["from"], lt["to"], lt["selector"], lt["value_eth"], lt["calldata_len"], (lt.get("input") or "")[:400])
        for a in e["adds"]: print(" add", a["bn"] - b0, a["ti"], a["li"], a["lo"], a["hi"], a["dl"], a["sender"][:10], a["tx"][:12], a["tx"] == p["launch_tx"])
        for a in e["pulls"]: print(" pull", a["bn"] - b0, a["ti"], a["li"], a["lo"], a["hi"], a["dl"], a["sender"][:10], a["tx"][:12])
        for s in e["swaps"][:20]:
            t = T.get(s["tx"])
            print(" swap", s["bn"] - b0, s["ti"], s["a0"], s["a1"], s["liq"], s["tick"], s["fee"], s["sender"][:10], t and (t["from"][:10], t["to"][:10], t["selector"], t["value_eth"], t["calldata_len"], t["nonce"]))
