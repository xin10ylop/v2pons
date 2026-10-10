import pickle, sys, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/explore")
P = pickle.load(open("pools.pkl", "rb"))
TX = pickle.load(open("../vbot/react/cache_tx.pkl", "rb"))
TX.update(pickle.load(open("../vbot/react/cache_tx2.pkl", "rb")))
ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
fam = sorted([p for p in P.values() if p.get("inlen") == 1444 and p.get("fee") == 2500 and p.get("ts") == 50], key=lambda p: p["b0"]) ; fam = [p for p in fam if "sw" in p]; print(len(fam))
kinds = collections.Counter(); tokin = collections.Counter(); cov = 0; tot = 0
first = collections.Counter()
for p in fam:
    tok = p["token"][2:].lower()
    for i, x in enumerate(p["sw"]):
        if x[0] - p["b0"] > 60: break
        tot += 1
        t = TX.get(x[7])
        if not t: continue
        cov += 1
        side = "buy" if x[2] < 0 else "sell"
        k = (side, t["to"][:10], t["value"] > 0, t["inlen"] if t["inlen"] < 2000 else ">2000", t["sel"])
        kinds[k] += 1
        tokin[(side, t["to"][:10], tok in t["input"].lower())] += 1
print("swaps <= +60:", tot, "with tx:", cov)
for k, v in kinds.most_common(20): print(" ", v, k)
print(tokin.most_common())
# example bot buy
for p in fam[200:201]:
    for x in p["sw"][:4]:
        t = TX.get(x[7]); print(x[0]-p["b0"], x[2]/1e18, t and {k: (v if k != "input" else v[:600]) for k, v in t.items()})
    print("token", p["token"])
