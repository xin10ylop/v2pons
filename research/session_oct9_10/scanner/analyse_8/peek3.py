import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families(); P = load_pools(); T = load_txs()
k = "0x05d552391067389ee44fec3924157ed33f976000|ce5494bb|36|10000|200|true"
pids = F[k]["pids"]
E = load_events(set(pids))
for pid in pids:
    p = P[pid]; e = E[pid]; L0 = p["launch_block"]
    lt = T[p["launch_tx"]]
    print("=====", pid[:10], L0, "from", p["launch_from"], "nonce", p["launch_nonce"], "tok", p["token"], "input", lt.get("input"))
    for a in e["adds"]: print("  add", a["bn"] - L0, a["lo"], a["hi"], a["dl"], a["sender"][:10], a["tx"][:10])
    for a in e["pulls"]: print("  pull", a["bn"] - L0, a["lo"], a["hi"], a["dl"], a["sender"][:10], T.get(a["tx"], {}).get("from"))
    for s in e["swaps"][:40]:
        t = T.get(s["tx"])
        print("  sw %5d ti%3d %+.6f liq %d tick %d %s" % (s["bn"] - L0, s["ti"], -s["a0"] / 1e18, s["liq"], s["tick"], t and (t["from"][:10], (t["to"] or "")[:10], t["selector"], t["calldata_len"], t["max_prio"], t["nonce"])))
