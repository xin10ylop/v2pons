import pickle, collections, sys, numpy as np
sys.path.insert(0, ".")
from fams import *
P = pickle.load(open("pools.pkl", "rb"))
FK = lambda p: p.get("to") == PM_POS and p.get("inlen") == 1444 and p.get("fee") == 2500 and p.get("ts") == 50 and abs((p.get("value") or 0) - 2.4333285) < 1e-9
ps = sorted([p for p in P.values() if FK(p)], key=lambda p: p["b0"])
print("pools", len(ps), "with logs", sum(1 for p in ps if "sw" in p))
print("hooks", collections.Counter(p["hooks"] for p in ps).most_common(2))
print("tick0", collections.Counter(p["tick0"] for p in ps).most_common(5))
print("sp0", collections.Counter(p["sp0"] for p in ps).most_common(3))
print("liq", collections.Counter(p["liq"] for p in ps).most_common(3))
print("nonce", collections.Counter(p["nonce"] for p in ps).most_common(12))
print("from distinct", len({p["from"] for p in ps}))
print("prio", collections.Counter(p["prio"] for p in ps).most_common(5))
print("txindex", collections.Counter(p["txindex"] for p in ps).most_common(5))
snd = collections.Counter(); 
for p in ps[:]:
    for x in p.get("sw", []):
        if x[0]-p["b0"] <= 60: snd[(x[6][:10], "B" if x[2]<0 else "S")] += 1
print("swap senders +60:", snd.most_common(10))
mlsnd = collections.Counter((m[6][:10], m[4] > 0) for p in ps for m in p.get("mls", []))
print("ML senders:", mlsnd.most_common(6))
for p in ps[:4] + ps[-3:]:
    b0 = p["b0"]
    print("==", p["pid"][:12], b0, "nonce", p["nonce"], "from", p["from"][:10], "tick0", p["tick0"], "liq %.3e" % p["liq"])
    for x in p["sw"][:14]:
        print("   +%d li%d %s eth %.5f tok %.3e snd %s L %.3e" % (x[0]-b0, x[1], "BUY " if x[2]<0 else "SELL", abs(x[2])/1e18, abs(x[3]), x[6][:10], x[5]))
    for m in p["mls"][:4]: print("   ML +%d dl %.3e lo %d hi %d snd %s" % (m[0]-b0, m[4], m[2], m[3], m[6][:10]))
