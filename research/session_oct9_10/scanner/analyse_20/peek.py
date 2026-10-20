import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common20 import *
K = json.load(open(os.path.join(HERE, "keys.json")))
P = load_pools(); F = load_families(); T = load_txs()
for k in K:
    f = F[k]; print("=" * 100); print(k); print({a: b for a, b in f.items() if a != "pids"})
    pids = f["pids"]; E = load_events(set(pids))
    for pid in pids:
        p = P[pid]; e = E.get(pid) or {}
        print(" pool", pid[:14], "lb", p["launch_block"], "ts", p["launch_ts"], "from", p["launch_from"], "nonce", p["launch_nonce"], "val", p["launch_value_eth"], "tok", p["token"], "hooks", p["hooks"], "fee", p["fee"], "ts", p["tick_spacing"], "tick0", p["tick0"], "liq", p["liq_launch"], "known", p["known"])
        print("   adds", [(a["bn"] - p["launch_block"], a["lo"], a["hi"], a["dl"], a["sender"][:10]) for a in e.get("adds", [])][:4])
        for s in e.get("swaps", [])[:14]:
            t = T.get(s["tx"]) or {}
            print("   sw +%d ti%d %s %.6f fee %s to %s from %s sel %s clen %s nonce %s" % (s["bn"] - p["launch_block"], s["ti"], "BUY " if s["a0"] < 0 else "SELL", abs(s["a0"]) / 1e18, s["fee"], (t.get("to") or "")[:12], (t.get("from") or "")[:12], t.get("selector"), t.get("calldata_len"), t.get("nonce")))
        print("   nswaps", len(e.get("swaps", [])), "pulls", [(x["bn"] - p["launch_block"], x["dl"], x["sender"][:10], (T.get(x["tx"]) or {}).get("from")) for x in e.get("pulls", [])][:3])
