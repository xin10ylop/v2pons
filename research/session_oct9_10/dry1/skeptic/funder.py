import sys, pickle
sys.path.insert(0, '/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad')
from chain import batch
cases = [("0x275aa5cb7cf6fc544d73caa51802b5010b35826c", 84862687 + 2), ("0xb74d65babe17f94ba6dee477eae3f56e00ec0864", 84862953 + 3), ("0x6fac2c52e8d3795171184cdd1aeead6986946225", 84867283 + 3)]
for w, bb in cases:
    lo = bb - 400
    bl = batch([("eth_getBlockByNumber", [hex(k), True]) for k in range(lo, bb + 1)])
    w2 = w[2:]
    hits = []
    for b in bl:
        for t in b["transactions"]:
            if (t["to"] or "").lower() == w or w2 in t["input"].lower() or t["from"].lower() == w:
                hits.append((int(b["number"], 16) - bb, t["from"], t["to"], int(t["value"], 16) / 1e18, t["input"][:10], len(t["input"]) // 2 - 1, t["hash"][:12]))
    print(w[:10], "buy at", bb, "hits", hits)
