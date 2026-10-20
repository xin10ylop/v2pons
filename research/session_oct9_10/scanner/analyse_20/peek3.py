import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common20 import *
P = load_pools(); T = load_txs()
pids = [p["pid"] for p in P.values() if p["hooks"] == "0x4e3468951d49f2eea976ed0d6e75ffcb44a9a544"]
E = load_events(set(pids))
for pid in pids:
    p = P[pid]; e = E.get(pid) or {}
    print("pool", pid, "lb", p["launch_block"], "fam", p["family"][:20], "from", p["launch_from"], "token", p["token"], "sqrt_p0", p["sqrt_p0"], "tick0", p["tick0"])
    print("  launch tx", p["launch_tx"], "to", p["launch_to"], "first8_to", p["first8_swap_to"])
    for a in e.get("adds", []): print("  add +%d" % (a["bn"] - p["launch_block"]), a["lo"], a["hi"], a["dl"], a["sender"], a["tx"][:12], (T.get(a["tx"]) or {}).get("from"))
    for s in e.get("swaps", [])[:40]:
        t = T.get(s["tx"]) or {}
        print("  sw +%d ti%d li%d %s a0 %.8f a1 %.4e fee %d L %d tick %d sender %s txto %s from %s tx %s" % (s["bn"] - p["launch_block"], s["ti"], s["li"], "BUY " if s["a0"] < 0 else "SELL", s["a0"] / 1e18, s["a1"], s["fee"], s["liq"], s["tick"], s["sender"][:12], (t.get("to") or "")[:12], (t.get("from") or "")[:12], s["tx"][:12]))
    print("  nswaps", len(e.get("swaps", [])), "zero_mods", len(e.get("zero_mods", [])))
