"""Walk a capital loop BACKWARD: at each wallet, list incoming value txs (scan back from `before`, keep 150 blocks past the first hit), tag
senders by family, then step to the largest sender. Usage: loopback.py addr before max_steps stop_block out.jsonl"""
import sys, os, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bc
from trace import T, tag, LA, incoming
DEP = {L["deployer"]: L for L in LA["launches"]}
def lab(x):
    if x in DEP: return "DEP:%s:%s" % (DEP[x]["family"], DEP[x]["utc"])
    t = tag(x); return t.replace("crowd_", "") if t else "-"
a, before, n, stop, out = sys.argv[1].lower(), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
fo = open(out, "a")
for step in range(n):
    inc, lo = incoming(a, before, maxback=20000, extra=150)
    if not inc:
        rec = {"step": step, "addr": a, "stop": "no incoming in %d..%d" % (lo, before - 1)}; print(json.dumps(rec), flush=True); fo.write(json.dumps(rec) + "\n"); break
    big = max(inc, key=lambda x: x["eth"])
    rec = {"step": step, "addr": a, "utc": big["utc"], "bn": big["bn"], "from": big["from"], "from_lab": lab(big["from"]), "from_nonce": big["nonce"], "eth": round(big["eth"], 4),
           "n_in": len(inc), "in_fams": dict(collections.Counter(lab(x["from"]) for x in inc)), "in_eth": round(sum(x["eth"] for x in inc), 4),
           "odd_in": [(x["from"], round(x["eth"], 4), x["nonce"]) for x in inc if lab(x["from"]) == "-" and x["eth"] > 0.3][:5]}
    print(json.dumps(rec), flush=True); fo.write(json.dumps(rec) + "\n")
    if big["nonce"] > 100 or big["bn"] < stop: break
    a, before = big["from"], big["bn"]
