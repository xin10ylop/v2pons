import sys, collections, json, datetime
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); T = load_txs()
g3 = [p for p in P.values() if (p["to_code_hash"] or "").replace("0x","").startswith("f07d1c53")]
E = load_events(set(p["pid"] for p in g3))
C = collections.Counter()
for p in g3:
    e = E[p["pid"]]; b0 = p["launch_block"]
    sw = e["swaps"]; pu = e["pulls"]
    s = " ".join("%s+%d:%.4f:%s" % ("B" if x["a0"]<0 else "S", x["bn"]-b0, abs(x["a0"])/1e18, ((T.get(x["tx"]) or {}).get("from") or "?")[:8]) for x in sw)
    pl = " ".join("P+%d:%s" % (x["bn"]-b0, ((T.get(x["tx"]) or {}).get("from") or "?")[:8]) for x in pu)
    print(datetime.datetime.utcfromtimestamp(p["launch_ts"]).strftime("%H:%M:%S"), b0, p["launch_from"][:8], "n%d" % p["launch_nonce"], p["hooks"][-4:], len(e["adds"]), s, "|", pl, "| zm", len(e["zero_mods"]))
    for x in sw: C[(T.get(x["tx"]) or {}).get("from")] += 1
print(C.most_common(10))
