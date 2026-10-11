"""Do sells by wallets outside the bot's crowd go through and return ETH? Every fetched sell tx (census + v07/v09/v13) in C-1 core pools by
a wallet that never called the router and is not the launch wallet: count, wallets, ETH out; matched round trips (the same wallet's
first buy and first later sell in the pool, both fetched): return on the ETH paid, blocks held, pulled-before-sell is not visible here."""
import pickle
from sim import *
rows = {r["pool"]: r for r in jl(os.path.join(V, "c1_rows.jsonl")) if r["quote"] == "ETH"}
E = pickle.load(open(os.path.join(V, "ev.pkl"), "rb"))
T = json.load(open(os.path.join(V, "c1_txs.json"))); T.update(json.load(open(os.path.join(V, "sample_txs.json"))))
crowd = {t["from"] for t in T.values() if t.get("to") == BOT}
sells = []; rts = []; wal = set(); routes = C.Counter()
for pid, r in rows.items():
    P = Pool(r, E[pid]); first_buy = {}
    for x in P.sw:
        t = T.get(x[8])
        if t is None or t["to"] == BOT or t["from"] in crowd or t["from"] == r["launch"]["from"]: continue
        w = t["from"]
        if x[3]: first_buy.setdefault(w, x)
        else:
            sells.append(x[4] / 1e18); wal.add(w); routes[f"{t['to'][:10]}:{t['selector']}"] += 1
            if w in first_buy and first_buy[w] is not None:
                b = first_buy[w]; rts.append(((x[4] - b[4]) / b[4], x[0] - b[0], b[4] / 1e18)); first_buy[w] = None
print(f"outsider sells fetched: {len(sells)} by {len(wal)} wallets, ETH out {sum(sells):.4f} (p50 {pct(sells,0.5):.6f}); routes {routes.most_common(5)}")
print(f"matched round trips: {len(rts)}; return on ETH in: mean {sum(a for a,_,_ in rts)/len(rts):+.3f} median {pct([a for a,_,_ in rts],0.5):+.3f} positive {sum(1 for a,_,_ in rts if a > 0)/len(rts):.0%}; held p10/50/90 {p3([b for _,b,_ in rts])}; buy size p50 {pct([c for _,_,c in rts],0.5):.5f} ETH, max {max(c for _,_,c in rts):.4f}")
big = [x for x in rts if x[2] >= 0.001]
if big: print(f"  round trips with a buy >= 0.001 ETH: {len(big)}; mean {sum(a for a,_,_ in big)/len(big):+.3f} median {pct([a for a,_,_ in big],0.5):+.3f}; held p50 {pct([b for _,b,_ in big],0.5)}")
