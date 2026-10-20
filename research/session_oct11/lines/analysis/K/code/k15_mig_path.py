"""post-migration price path in the v4 pools (offline, census events): price in ETH per token from sqrtPriceX96 (ETH = currency0), relative to
the migration price; buy/sell flow; the hook's fee field."""
import json, collections, statistics as st
from krpc import *
M = {m["pool"]: m for m in json.load(open(os.path.join(OUT, "k13_mig_pools.json")))}
E = json.load(open(os.path.join(DATA, "mig_pool_events.json")))
def px(s): return 1.0 / ((s / 2**96) ** 2)   # ETH per token (token = currency1)
offs = [0, 1, 2, 5, 10, 20, 50, 100, 300, 1000, 3000]
rows = []; fees = collections.Counter(); senders = collections.Counter()
for pid, ev in E.items():
    m = M[pid]; lb = m["launch_block"]; p0 = px(m["sqrt_p0"])
    sw = [e for e in ev if e[0] == "s"]; ml = [e for e in ev if e[0] == "m"]
    for e in sw: fees[e[11]] += 1; senders[e[5]] += 1
    path = {}
    for o in offs:
        last = [e for e in sw if e[1] <= lb + o]
        path[o] = px(last[-1][8]) / p0 if last else 1.0
    mx = max([px(e[8]) / p0 for e in sw] or [1.0]); mn = min([px(e[8]) / p0 for e in sw] or [1.0])
    buys = [e for e in sw if e[6] < 0]; sells = [e for e in sw if e[6] > 0]
    b10 = sum(-e[6] for e in buys if e[1] <= lb + 10) / 1e18; s10 = sum(e[6] for e in sells if e[1] <= lb + 10) / 1e18
    rows.append({"pool": pid, "lb": lb, "p0_eth_per_token": p0, "n_swaps": len(sw), "n_buys": len(buys), "n_sells": len(sells), "buy_eth": sum(-e[6] for e in buys) / 1e18,
                 "sell_eth": sum(e[6] for e in sells) / 1e18, "buy_eth_10": b10, "sell_eth_10": s10, "path": path, "max": mx, "min": mn, "n_liq": len(ml),
                 "liq_events": [[e[1] - lb, e[6], e[7], e[8]] for e in ml][:4]})
json.dump(rows, open(os.path.join(OUT, "k15_mig_path.json"), "w"))
print("pools", len(rows), "swap fee field", fees.most_common(5), "top senders", senders.most_common(5))
print("p0 eth/token median", st.median(r["p0_eth_per_token"] for r in rows), "(curve final 5.88/285.714M =", 5.88 / 285714285.714, ")")
for o in offs:
    v = sorted(r["path"][o] for r in rows)
    print(f"+{o:5d} blocks: price/p0 p10 {v[len(v)//10]:.3f} p25 {v[len(v)//4]:.3f} median {v[len(v)//2]:.3f} p75 {v[3*len(v)//4]:.3f} p90 {v[9*len(v)//10]:.3f} mean {sum(v)/len(v):.3f}")
print("liq events in pool (first rows)", [r["liq_events"] for r in rows[:3]])
print("n_liq dist", collections.Counter(r["n_liq"] for r in rows).most_common(5))
print("buy ETH in 3000 blocks median", st.median(r["buy_eth"] for r in rows), "sell", st.median(r["sell_eth"] for r in rows), "buy in first 10 blocks median", st.median(r["buy_eth_10"] for r in rows))
print("max/p0 median", st.median(r["max"] for r in rows), "min/p0 median", st.median(r["min"] for r in rows))
