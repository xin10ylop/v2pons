import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); T = load_txs()
dep = "0x841ac064763c75a6b6b916ef676420d6ffdd281f"
pids = [p["pid"] for p in P.values() if p["launch_from"] == dep]
E = load_events(set(pids))
for pid in pids:
    p = P[pid]; e = E[pid]
    print("--", pid[:12], p["family"].split("|")[0][:12], "fee", p["fee"], "lb", p["launch_block"], "val", p["launch_value_eth"], "nonce", p["launch_nonce"], "pulls", len(e["pulls"]), "ts", p["launch_ts"])
    lt = T[p["launch_tx"]]
    inp = lt.get("input") or lt["input512"]
    print("   launch input words:", [inp[10+64*i:10+64*(i+1)] for i in range((len(inp)-10)//64)])
    for s in e["swaps"]:
        t = T.get(s["tx"])
        print("   swap +%d ti%d a0 %.8f a1 %d fee %d" % (s["bn"]-p["launch_block"], s["ti"], -s["a0"]/1e18, s["a1"], s["fee"]), s["sender"][:10], (t["to"][:10], t["from"][:10], t["selector"], t["nonce"], t["value_eth"]) if t else None)
        if t and t["selector"] == "08c1284c":
            inp = t.get("input") or t["input512"]
            print("      words:", [inp[10+64*i:10+64*(i+1)].lstrip("0") or "0" for i in range((len(inp)-10)//64)])
