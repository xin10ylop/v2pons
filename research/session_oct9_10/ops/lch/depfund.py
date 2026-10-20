"""For a launcher deployer: its funding tx, the funder's fan-out (families), the funder's own funding (consolidation) and that one's inputs.
Usage: depfund.py deployer launch_block"""
import sys, os, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bc
from trace import T, tag, LA, incoming, outgoing
DEP = {L["deployer"]: L for L in LA["launches"]}
POP = {}
for r in json.load(open(os.path.dirname(os.path.abspath(__file__)) + "/population.json")): POP.setdefault(r["frm"], []).append(r)
def lab(x):
    if x in DEP: return "DEP:%s:%s" % (DEP[x]["family"], DEP[x]["utc"])
    if x in POP: return "LAUNCHER_DEPLOYER(blk %d)" % POP[x][0]["bn"]
    t = tag(x); return t.replace("crowd_", "") if t else "-"
d, b = sys.argv[1].lower(), int(sys.argv[2])
inc, lo = incoming(d, b, maxback=20000, extra=150)
print("deployer", d, "launch blk", b, "incoming:", [(x["from"], round(x["eth"], 4), x["nonce"], x["utc"], x["bn"]) for x in inc])
if inc:
    f = max(inc, key=lambda x: x["eth"])
    o, _ = outgoing(f["from"], f["bn"] - 100, maxfwd=600, want=200, extra=150)
    print("  funder", f["from"], "fan-out", len(o), dict(collections.Counter(lab(x["to"]) for x in o)), "total %.3f" % sum(x["eth"] for x in o))
    inc2, _ = incoming(f["from"], f["bn"], maxback=20000, extra=150)
    print("  funder's funding:", [(x["from"], round(x["eth"], 4), x["nonce"], x["utc"]) for x in inc2][:3])
    if inc2:
        g = max(inc2, key=lambda x: x["eth"])
        inc3, _ = incoming(g["from"], g["bn"], maxback=20000, extra=150)
        print("  consolidation", g["from"], "inputs", len(inc3), dict(collections.Counter(lab(x["from"]) for x in inc3)), "total %.3f" % sum(x["eth"] for x in inc3))
        for x in inc3:
            if lab(x["from"]) in ("-",) or lab(x["from"]).startswith(("LAUNCHER", "DEP")):
                print("     input", x["from"], lab(x["from"]), round(x["eth"], 4), "nonce", x["nonce"], x["utc"])
