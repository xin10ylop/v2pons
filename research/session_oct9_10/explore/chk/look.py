import pickle, sys, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/explore")
from fams import *
P = pickle.load(open("pools.pkl", "rb"))
fam = [p for p in P.values() if p.get("inlen") == 1444 and p.get("fee") == 2500 and p.get("ts") == 50 and p.get("to") == PM_POS]
print(len(fam), collections.Counter(round(p["value"], 7) for p in fam).most_common(5))
print(collections.Counter(p["from"] for p in fam).most_common(10))
print(collections.Counter(p["code"] for p in fam).most_common(5))
fam.sort(key=lambda p: p["b0"])
for p in fam[100:103]:
    print("=====", p["pid"], p["b0"], "from", p["from"], "nonce", p["nonce"], "liq", p["liq"], "value", p["value"], "txindex", p["txindex"], "token", p["token"])
    for m in p["mls"][:5]: print("   ML", m[0] - p["b0"], m[2], m[3], m[4], m[5][:12], m[6])
    for x in p["sw"][:40]:
        print("   SW", x[0] - p["b0"], x[1], "a0 %.5f" % (x[2] / 1e18), "a1 %.4g" % x[3], "L %.4g" % x[5], x[6], x[7][:12])
