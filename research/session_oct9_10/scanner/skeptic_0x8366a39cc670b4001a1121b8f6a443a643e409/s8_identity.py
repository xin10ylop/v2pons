import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_s import *
C = load_cache(); R = json.load(open(os.path.join(HERE, "timeline.json")))
loop = json.load(open("/home/user/v2pons/research/session_oct9_10/money/loop.json"))
opA = set(loop["crowd"]) | set(loop["disp"]) | set(loop["sweeps"]) | {a for ch in loop["chains"] for a in ch}
opA |= {"0x3194e32622c5d860a0572c74edda99dcfd8fc827", "0x3b11cafa6b570e3bc75bb6529b16dd35fe4b64b5"}
vb = {"0x1cbaf24d53fe930fce8eff149fa797d2611da149", "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc", "0xfd1b271f235e5230eaee9d914ccb1af495bfb758"}
vb_prefix = ("0x488faf52", "0x259a1b7b", "0x93b07902")
keepers = collections.Counter(); sellers = collections.Counter(); routers = collections.Counter()
for r in R:
    for x in r["swaps"]:
        if x["cls"] == "crowd":
            (keepers if x["buy"] else sellers)[x["from"]] += 1; routers[(x["to"], "buy" if x["buy"] else "sell")] += 1
allw = set(keepers) | set(sellers)
print("keepers (buy)", len(keepers), "sellers", len(sellers), "both", len(set(keepers) & set(sellers)))
print("crowd routers", routers)
print("overlap with operator A lists", allw & opA, "with vbot", allw & vb, [w for w in allw if w.startswith(vb_prefix)])
deps = {r["deployer"] for r in R}
print("deployers overlap opA", deps & opA, "keepers", deps & allw)
# all tx participants in these pools vs operator A crowd
parts = {x["from"] for r in R for x in r["swaps"] if x["from"]}
print("any swap tx sender in operator A lists", parts & opA)
# keeper nonces, gas price
kn = [C[h]["nonce"] for h in C if C[h]["to"] in CROWD_ROUTERS]
gp = collections.Counter(C[h]["gp"] for h in C if C[h]["to"] in CROWD_ROUTERS)
print("keeper nonce q", q(kn, (0, .5, 1)), "gas prices top", gp.most_common(5))
# who sends the sells: same keepers? sell recipient
ex = [C[h] for h in C if C[h]["to"] in CROWD_ROUTERS and C[h]["len"] == 804][:2]
for t in ex:
    print("SELL", t["from"], t["to"], t["nonce"])
    for i, w in enumerate(words(t["input"])): print("   ", i, w)
