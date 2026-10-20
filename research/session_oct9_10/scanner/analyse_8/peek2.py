import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools()
v = [p for p in P.values() if p["known"] == "vbot-v2.433"]
a = [p for p in P.values() if p["known"] == "operator-A"]
print(len(v), len(a))
E = load_events({v[100]["pid"], v[-5]["pid"], a[3]["pid"]})
T = load_txs()
for p in (v[100], v[-5], a[3]):
    e = E[p["pid"]]
    print(json.dumps({k: p[k] for k in p if k not in ()}, default=str)[:1500])
    for s in e["swaps"][:14]:
        t = T.get(s["tx"])
        print("  sw", s["bn"] - p["launch_block"], s["ti"], s["li"], s["sender"][:10], s["a0"] / 1e18, s["fee"], s["liq"], t and (t["from"][:10], (t["to"] or "")[:10], t["selector"], t["calldata_len"]))
    for s in e["pulls"][:3]: print("  pull", s["bn"] - p["launch_block"], s["sender"][:10], s["dl"])
    for s in e["adds"][:3]: print("  add", s["bn"] - p["launch_block"], s["lo"], s["hi"], s["dl"])
