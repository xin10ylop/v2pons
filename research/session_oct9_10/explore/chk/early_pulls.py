import pickle, collections
P = pickle.load(open("pools.pkl", "rb"))
TX = pickle.load(open("../vbot/react/cache_tx.pkl", "rb")); TX.update(pickle.load(open("../vbot/react/cache_tx2.pkl", "rb")))
ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
BOTW = {t["from"] for t in TX.values() if t["to"] == ROUTER}
TRIO = {"0xe71a69f434a719cd5afa411568b69716aab3b84a": "dustA", "0xf6e55480c5939da146092301e388654879c6e6fb": "dustB", "0xb002e8a04b2822d8f2890b022ddea3d25f9c3df8": "dustC"}
fam = sorted([p for p in P.values() if p.get("inlen") == 1444 and p.get("fee") == 2500 and p.get("ts") == 50 and "sw" in p], key=lambda p: p["b0"])
n = 0
for p in fam:
    neg = [m for m in p["mls"] if m[4] < 0]
    if not neg or neg[0][0] - p["b0"] > 45: continue
    pr = neg[0][0] - p["b0"]; pt = TX.get(neg[0][5])
    seq = []
    for x in p["sw"]:
        if x[0] > neg[0][0]: break
        t = TX.get(x[7]); w = t["from"] if t else "?"
        who = "dep" if w == p["from"] else ("bot" if (t and (t["to"] == ROUTER or w in BOTW)) else TRIO.get(w, "OUT:" + w[:8]))
        seq.append(f"+{x[0]-p['b0']}{'B' if x[2] < 0 else 'S'}{abs(x[2])/1e18:.4f}{who}")
    print(f"{p['pid'][:10]} pull +{pr} by {'dep' if pt and pt['from']==p['from'] else (pt['from'][:10] if pt else '?')} via {pt['to'][:10] if pt else '?'} | " + " ".join(seq))
    n += 1
print(n)
