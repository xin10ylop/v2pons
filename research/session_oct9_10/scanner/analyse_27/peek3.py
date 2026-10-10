import sys, collections, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); T = load_txs()
g3 = [p for p in P.values() if (p["to_code_hash"] or "").replace("0x","").startswith("f07d1c53")]
E = load_events(set(p["pid"] for p in g3))
for p in g3[:6] + g3[-3:]:
    e = E[p["pid"]]
    print("=====", p["pid"][:12], "b0", p["launch_block"], "ti", p["tx_index"], "from", p["launch_from"][:10], "nonce", p["launch_nonce"], "to", p["launch_to"][:10], "created", p["created_contract"], "hooks", p["hooks"][:12], "sqrt", p["sqrt_p0"], "tick0", p["tick0"], "liq", p["liq_launch"], "buy_in_launch", p["buy_in_launch_tx"], "codesize", p["to_code_size"])
    for a in e["adds"]: print("   add", a["bn"]-p["launch_block"], a["lo"], a["hi"], a["dl"], a["sender"][:10], a["tx"][:10], a["tx"]==p["launch_tx"])
    for s in e["swaps"][:12]:
        t = T.get(s["tx"]) or {}
        print("   swap +%d ti %d %s eth %.6f fee %d sender %s to %s from %s sel %s clen %s nonce %s" % (s["bn"]-p["launch_block"], s["ti"], "BUY " if s["a0"]<0 else "SELL", abs(s["a0"])/1e18, s["fee"], s["sender"][:10], (t.get("to") or "")[:10], (t.get("from") or "")[:10], t.get("selector"), t.get("calldata_len"), t.get("nonce")))
    print("   nswaps", len(e["swaps"]))
    for x in e["pulls"]:
        t = T.get(x["tx"]) or {}
        print("   pull +%d ti %d dl %d sender %s to %s from %s sel %s" % (x["bn"]-p["launch_block"], x["ti"], x["dl"], x["sender"][:10], (t.get("to") or "")[:10], (t.get("from") or "")[:10], t.get("selector")))
