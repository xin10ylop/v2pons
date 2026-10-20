"""Scan full blocks [a, b] for transactions from / to a wallet or naming it in the input (funding, first tx). Usage: scan_funding.py w a b"""
import sys, json, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
w = sys.argv[1].lower(); a, b = int(sys.argv[2]), int(sys.argv[3])
hits = []; n = 0
for s in range(b, a - 1, -50):
    lo = max(a, s - 49)
    blks = batch([("eth_getBlockByNumber", [hex(x), True]) for x in range(lo, s + 1)])
    for blk in blks:
        if not blk: continue
        for t in blk["transactions"]:
            n += 1
            if t["from"].lower() == w or (t.get("to") or "").lower() == w or w[2:] in t["input"].lower():
                hits.append((int(blk["number"], 16), time.strftime("%m-%d %H:%M:%S", time.gmtime(int(blk["timestamp"], 16))), t["hash"], t["from"], t.get("to"), int(t["value"], 16) / 1e18, t["input"][:10], int(t["nonce"], 16)))
    if len(sys.argv) < 5 and any((h[4] or "").lower() == w and h[5] > 0 for h in hits): break       # 4th arg "all": scan the whole window
for h in sorted(hits): print(h)
print("scanned txs", n)
