"""All txs from/to the given wallets in [a, b] (fetching blocks as needed). Usage: wtx.py a b addr [addr...]"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bc
from trace import T, tag, LA
DEP = {L["deployer"]: L for L in LA["launches"]}
def lab(x):
    if x in DEP: return "DEP:%s:%s" % (DEP[x]["family"], DEP[x]["utc"])
    t = tag(x); return t.replace("crowd_", "") if t else ""
a, b = int(sys.argv[1]), int(sys.argv[2]); W = {x.lower() for x in sys.argv[3:]}
for bn, ts, t in bc.txs(a, b):
    if t[1] in W or t[2] in W:
        x = T(bn, ts, t); print(x["utc"], bn, x["from"], lab(x["from"]), "->", x["to"], lab(x["to"]), round(x["eth"], 5), "nonce", x["nonce"], x["sel"], x["len"], x["hash"], flush=True)
