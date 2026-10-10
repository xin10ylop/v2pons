import pickle, collections, sys, numpy as np
sys.path.insert(0, ".")
from fams import *
P = pickle.load(open("pools.pkl", "rb")); M = pickle.load(open("meta.pkl", "rb")); pids = M["pids"]; F = families(P, pids)
TX = pickle.load(open("../vbot/cache_tx.pkl", "rb"))
for fk in ("L:0x58daec31|0xac9650d8|len1444|fee2500|ts50|v2.433", "L:0x58daec31|0xac9650d8|len1444|fee10000|ts200|v5.0", "L:0x58daec31|0xac9650d8|len1444|fee10000|ts200|v3.0",
           "L:0x8366a39c|0x6276cbbe|len196|fee500|ts1|v0"):
    ps = [P[pids[i]] for i in F[fk]]
    print("==", fk, len(ps))
    print("  exact launch value (ETH):", collections.Counter(p["value"] for p in ps).most_common(3), " sel/len:", collections.Counter((p["sel"], p["inlen"]) for p in ps).most_common(2),
          " nonce:", collections.Counter(nb(p["nonce"]) for p in ps).most_common(4), " txindex<=3:", sum(1 for p in ps if p["txindex"] <= 3) / len(ps))
    fb = []; pre = []; after_pre = []
    for p in ps:
        b0 = p["b0"]
        big = [x for x in p["sw"] if -x[2] >= 0.01e18]
        if not big: continue
        t1 = big[0][0] - b0; fb.append(t1)
        early = [x for x in p["sw"] if x[2] < 0 and x[0] < big[0][0] and -x[2] >= 0.0005e18]
        if early:
            pre.append((p["pid"][:10], [(x[0] - b0, round(-x[2] / 1e18, 4), TX.get(x[7], {}).get("from", "?")[:10]) for x in early][:3], t1, round(-big[0][2] / 1e18, 3)))
    fb = np.array(fb)
    print("  first >=0.01 buy offset: p5/p10/p25/p50/p90", np.percentile(fb, [5, 10, 25, 50, 90]), " share <= +3:", round((fb <= 3).mean(), 3), "<= +5:", round((fb <= 5).mean(), 3), "<= +7:", round((fb <= 7).mean(), 3))
    print("  pools with a >=0.0005 ETH buy before the first big buy:", len(pre))
    for x in pre[:6]: print("    ", x)
