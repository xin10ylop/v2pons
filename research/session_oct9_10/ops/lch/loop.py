"""Walk a rolling capital loop forward: at each wallet take its first plain ETH transfer > MIN (the capital), log fan-outs (distributor ->
creator + crowd) and fan-ins (crowd + creator -> consolidation wallet), tagging every counterparty by crowd family (A/B/fresh) or as a
launch deployer. Usage: loop.py start_addr start_block max_steps until_block out.jsonl"""
import sys, os, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bc
from trace import T, tag, LA
DEP = {L["deployer"]: L for L in LA["launches"]}
MIN = 0.05
def lab(x):
    if x in DEP: return "DEP:%s:%s" % (DEP[x]["family"], DEP[x]["utc"])
    t = tag(x); return t.replace("crowd_", "") if t else "-"
a, s, n, until, out = sys.argv[1].lower(), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
fo = open(out, "a")
for step in range(n):
    # all txs from a after s (up to 6000 blocks, stop 150 blocks after first plain >MIN transfer)
    txs = []; first = None
    for bn, ts, t in bc.txs(s, min(until, s + 20000)):
        if first is not None and bn > first + 150: break
        if t[1] == a:
            x = T(bn, ts, t); txs.append(x)
            if first is None and x["sel"] == "0x" and x["eth"] > MIN: first = bn
    if first is None:
        rec = {"step": step, "addr": a, "stop": "no plain transfer > %.2f before %d" % (MIN, min(until, s + 20000)), "calls": [(x["to"], x["sel"], x["eth"]) for x in txs][:10]}
        print(json.dumps(rec), flush=True); fo.write(json.dumps(rec) + "\n"); break
    plain = [x for x in txs if x["sel"] == "0x" and x["eth"] > 0]
    calls = [x for x in txs if x["sel"] != "0x"]
    cap = next(x for x in plain if x["eth"] > MIN and x["bn"] == first)
    # incoming to a in the 120 blocks before its first tx (fan-in)
    a0 = txs[0]["bn"]
    ins = [T(bn, ts, t) for bn, ts, t in bc.txs(a0 - 120, a0) if t[2] == a and int(t[3]) > 0]
    rec = {"step": step, "addr": a, "nonce0": txs[0]["nonce"], "utc": cap["utc"], "bn": cap["bn"], "cap_to": cap["to"], "cap_eth": round(cap["eth"], 4),
           "n_plain_out": len(plain), "out_fams": dict(collections.Counter(lab(x["to"]) for x in plain)), "out_eth": round(sum(x["eth"] for x in plain), 4),
           "n_in": len(ins), "in_fams": dict(collections.Counter(lab(x["from"]) for x in ins)), "in_eth": round(sum(x["eth"] for x in ins), 4),
           "calls": sorted(set((x["to"], x["sel"]) for x in calls))[:6], "cap_to_lab": lab(cap["to"]),
           "odd_in": [(x["from"], round(x["eth"], 4), x["nonce"]) for x in ins if lab(x["from"]) == "-" and x["eth"] > 0.3][:5]}
    print(json.dumps(rec), flush=True); fo.write(json.dumps(rec) + "\n")
    if cap["bn"] >= until: break
    a, s = cap["to"], cap["bn"]
