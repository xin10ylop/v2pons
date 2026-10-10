import pickle, sys, collections
sys.path.insert(0, "/home/user/v2pons/src"); import v4math
P = pickle.load(open("pools.pkl", "rb"))
TX = pickle.load(open("../vbot/react/cache_tx.pkl", "rb")); TX.update(pickle.load(open("../vbot/react/cache_tx2.pkl", "rb")))
fam = sorted([p for p in P.values() if p.get("inlen") == 1444 and p.get("fee") == 2500 and p.get("ts") == 50 and "sw" in p], key=lambda p: p["b0"])
def wd(inp, i): return int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)
qc = collections.Counter(); seen = collections.Counter(); unseen = collections.Counter(); kinds = collections.Counter()
for p in fam:
    states = [(p["b0"], p["sp0"], p["sw"][0][5], "launch")]
    nb = 0
    for x in p["sw"]:
        t = TX.get(x[7])
        if t and t["sel"] == "0xc1120e3d" and x[2] < 0 and nb < 3:
            mo = wd(t["input"], 4); X = t["value"]
            r = [mo / v4math.buy_out_int(sp, L, X, 2500) for (b, sp, L, w) in states]
            ks = [k for k in range(len(r)) if abs(r[k] - 0.99) < 2e-6]
            if not ks: qc[(nb, "none")] += 1
            else:
                k = ks[-1]
                qc[(nb, "launch" if k == 0 else "after swap")] += 1
                if k + 1 < len(states): unseen[(nb, x[0] - states[k + 1][0], states[k+1][3])] += 1
                if k >= 1: seen[(nb, x[0] - states[k][0])] += 1
            nb += 1
        tt = TX.get(x[7]); w = (tt["to"][:10] + ("B" if x[2] < 0 else "S")) if tt else "?"
        states.append((x[0], x[4], x[5], w))
print(qc)
print("first bot buy: earliest swap NOT in its quote, (lag blocks, who):", sorted([(k, v) for k, v in unseen.items() if k[0] == 0], key=lambda z: -z[1])[:15])
print("first bot buy: latest swap IN its quote, lag:", sorted([(k, v) for k, v in seen.items() if k[0] == 0], key=lambda z: -z[1])[:10])
print("2nd bot buy: unseen", sorted([(k, v) for k, v in unseen.items() if k[0] == 1], key=lambda z: -z[1])[:10])
print("2nd bot buy: seen", sorted([(k, v) for k, v in seen.items() if k[0] == 1], key=lambda z: -z[1])[:10])
