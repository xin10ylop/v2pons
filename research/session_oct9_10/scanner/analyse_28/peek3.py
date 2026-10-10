import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); ids = json.load(open("pids.json"))
E = load_events(set(ids["F1"] + ids["F2"])); T = load_txs()
for fam in ("F2", "F1"):
    print("=======", fam)
    for pid in ids[fam]:
        p = P[pid]; e = E.get(pid)
        if not e or not e["swaps"]: continue
        print("--", pid[:10], "b0", p["launch_block"], "tick0", p["tick0"], "L", p["liq_launch"], "adds", [(a["lo"], a["hi"], a["dl"], a["bn"]-p["launch_block"]) for a in e["adds"]], "pulls", len(e["pulls"]), "zm", len(e["zero_mods"]))
        for s in e["swaps"][:14]:
            t = T.get(s["tx"])
            print("   +%d ti%d %s a0 %.6f a1 %.4g fee %d tick %d sender %s | %s" % (s["bn"]-p["launch_block"], s["ti"], "BUY " if s["a0"]<0 else "SELL", -s["a0"]/1e18, s["a1"]/1e18, s["fee"], s["tick"], s["sender"][:10],
                  (t["from"][:10] + " -> " + (t["to"] or "")[:10] + " sel " + t["selector"] + " len %d val %.6f nonce %d" % (t["calldata_len"], t["value_eth"], t["nonce"])) if t else "-"))
