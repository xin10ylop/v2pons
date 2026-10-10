import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common17 import *
P = load_pools(); T = load_txs(); F = load_families(); M = load_blocks_meta()
keys = json.load(open(os.path.join(HERE, "keys.json")))
for k in keys:
    f = F[k]; print("=" * 100); print(k)
    print({a: f[a] for a in f if a not in ("pids",)})
    E = load_events(set(f["pids"]))
    for pid in f["pids"]:
        p = P[pid]; e = E.get(pid) or {"swaps": [], "pulls": [], "adds": []}
        print("-- pool", pid[:12], "b0", p["launch_block"], "from", p["launch_from"][:10], "nonce", p["launch_nonce"], "value", p["launch_value_eth"], "token", p["token"][:10],
              "hooks", p["hooks"][:10], "fee", p["fee"], "liq", p["liq_launch"], "sqrt", p["sqrt_p0"], "tick0", p["tick0"], "nsw", p["n_swaps"], "pull", p["first_pull_rel"], p["first_pull_to"], p["first_pull_selector"], p["first_pull_from"])
        for a in e["adds"][:4]: print("   add", a["bn"] - p["launch_block"], a["lo"], a["hi"], a["dl"], a["sender"][:10], a["tx"][:10])
        for s in e["swaps"][:14]:
            t = T.get(s["tx"])
            print("   sw +%d ti%d %s eth %.6g fee %d sender %s to %s from %s sel %s clen %s" % (s["bn"] - p["launch_block"], s["ti"], "BUY " if s["a0"] < 0 else "SELL", abs(s["a0"]) / 1e18, s["fee"], s["sender"][:10],
                  (t["to"] or "")[:10] if t else None, t["from"][:10] if t else None, t["selector"] if t else None, t["calldata_len"] if t else None))
        for pl in e["pulls"][:3]: print("   pull +%d dl %d sender %s tx %s" % (pl["bn"] - p["launch_block"], pl["dl"], pl["sender"][:10], pl["tx"][:10]))
