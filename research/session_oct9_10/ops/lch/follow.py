"""Follow ETH forward through single-output hops until it fans out (a distributor) or stops.
Usage: follow.py addr start_block maxhops [maxfwd]"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bc
from trace import T, outgoing, tag, LA
DEP = {L["deployer"]: L for L in LA["launches"]}
a, s, n = sys.argv[1].lower(), int(sys.argv[2]), int(sys.argv[3]); mf = int(sys.argv[4]) if len(sys.argv) > 4 else 40000
def lab(x):
    if x in DEP: return "DEPLOYER of %s %s %s" % (DEP[x]["utc"], DEP[x]["family"], DEP[x]["pid"][:10])
    return tag(x)
for i in range(n):
    o, hi = outgoing(a, s, maxfwd=mf, want=200, extra=150)
    if not o: print(i + 1, a, "no outgoing tx in", s, hi, flush=True); break
    big = [x for x in o if x["eth"] > 0.01]
    print(i + 1, a, "sends", len(o), "txs:", flush=True)
    for x in o[:40]: print("     ", x["utc"], x["bn"], "->", x["to"], round(x["eth"], 5), "nonce", x["nonce"], x["sel"], lab(x["to"]), flush=True)
    if len(big) != 1: break
    a, s = big[0]["to"], big[0]["bn"]
