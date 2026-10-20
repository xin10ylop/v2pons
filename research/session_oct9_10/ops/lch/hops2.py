"""Backward funding chain with all txs of each wallet listed in a window: for addr, list incoming value txs (scan back up to maxback from `before`,
stop 300 blocks after the first hit), pick the largest, repeat. Usage: hops2.py addr before nhops [maxback]"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trace import incoming, tag, LA
DEP = {L["deployer"]: L for L in LA["launches"]}
a, before, n = sys.argv[1].lower(), int(sys.argv[2]), int(sys.argv[3]); mb = int(sys.argv[4]) if len(sys.argv) > 4 else 40000
for i in range(n):
    inc, lo = incoming(a, before, maxback=mb, extra=300)
    if not inc: print(i + 1, a, "NO incoming in", lo, before - 1, flush=True); break
    for x in inc: print(i + 1, a[:12], "<-", x["from"], tag(x["from"]), ("DEPLOYER " + DEP[x["from"]]["utc"]) if x["from"] in DEP else "", round(x["eth"], 5), "nonce", x["nonce"], x["utc"], x["bn"], x["hash"][:14], flush=True)
    f = max(inc, key=lambda x: x["eth"])
    if f["nonce"] > 100: print("   stop: largest funder", f["from"], "nonce", f["nonce"], flush=True); break
    a, before = f["from"], f["bn"]
