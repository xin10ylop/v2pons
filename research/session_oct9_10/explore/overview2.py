import pickle, collections, statistics as st, math
P = pickle.load(open("pools.pkl", "rb"))
Z = "0x" + "0" * 40
G = collections.defaultdict(list)
for p in P.values():
    if "sw" not in p or p["hooks"] != Z: continue
    G[(p["to"] if not (p["to"] or "").startswith("create:") else "create", p["sel"], p["inlen"], p["fee"], p["ts"], round(p["value"] or 0, 3))].append(p)
def rng(p):
    adds = [(m[2], m[3]) for m in p["mls"] if m[5] == p["tx"] and m[4] > 0]
    return tuple(sorted((lo - p["tick0"], hi - p["tick0"]) for lo, hi in adds))[:3]
for k, v in sorted(G.items(), key=lambda kv: -len(kv[1])):
    nreal = [sum(1 for x in p["sw"] if -x[2] >= 2e14) for p in v]
    if sum(1 for n in nreal if n) < 8: continue
    print("==", k, "n", len(v), "with_real", sum(1 for n in nreal if n), "deployers", len({p["from"] for p in v}))
    print("   tick0", collections.Counter(p["tick0"] for p in v).most_common(4))
    print("   range", collections.Counter(rng(p) for p in v).most_common(4))
    print("   nonce", collections.Counter(min(p["nonce"], 10) if p["nonce"] is not None else None for p in v).most_common(5), "prio", collections.Counter(p["prio"] for p in v).most_common(4))
    print("   liq", collections.Counter(int(math.log10(p["liq"])) if p["liq"] else 0 for p in v).most_common(4), "txindex", collections.Counter(p["txindex"] for p in v).most_common(3))
    print("   nreal p10/50/90", sorted(nreal)[len(nreal)//10], sorted(nreal)[len(nreal)//2], sorted(nreal)[9*len(nreal)//10])
