#!/usr/bin/env python3
"""The deployer's reaction to outside buys, all PM1444 v3.0 pools (reaction.json from reaction.py, run without a filter).
An outside buy: not the volume bot (router 0x1cbaf24d c1120e3d), not 0xe71a69f4 (the +3 dust on every pool), not the deployer, not
0x93b07902 (0.000024 ETH at +120..180 on almost every pool, never followed by a pull: whitelisted). The first such buy per pool, the
delay to the pool's first liquidity removal. Writes reaction_cdf.json."""
import os, json, collections, statistics as st, time
HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(HERE, "reaction.json")))
WL = {"0x93b07902"}
full = [r for r in rows if not any(b["cls"] == "?" for b in r["buys"])]
out = {"pools": len(rows), "pools_with_all_buy_txs": len(full)}
def summ(sel, name):
    d = []; never = 0; ex = []
    for r in full:
        o = [b for b in r["buys"] if b["cls"] == "OUTSIDE" and (b["from"] or "")[:10] not in WL and sel(b)]
        if not o: continue
        if r["pull_off"] is None or r["pull_off"] < o[0]["off"]: never += 1; ex.append((r["b0"], o[0]["off"], o[0]["from"][:10], o[0]["eth"])); continue
        d.append(r["pull_off"] - o[0]["off"])
    N = len(d) + never
    if not N: return None
    res = {"n": N, "pulled_after": len(d), "never": never, "median": st.median(d) if d else None,
           "cdf": {h: round(sum(1 for x in d if x <= h) / N, 3) for h in (2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 60)}, "delays": sorted(d), "never_examples": ex[:8]}
    out[name] = res
    print(f"{name}: n {N} pulled after {len(d)} never {never} median {res['median']} cdf {res['cdf']}")
    return res
for per in ("census", "new", None):
    f = (lambda r: True) if per is None else (lambda r, per=per: r["src"] == per)
    sub = [r for r in full if f(r)]
    saved = full
    full = sub
    tag = per or "all"
    summ(lambda b: True, f"{tag}/any")
    summ(lambda b: b["eth"] >= 1e-4, f"{tag}/>=0.0001")
    summ(lambda b: b["eth"] >= 1e-4 and b["off"] >= 8, f"{tag}/>=0.0001,off>=8")
    summ(lambda b: b["eth"] < 1e-4, f"{tag}/<0.0001")
    full = saved
# the pools without any (non-whitelisted) outside buy: how early are they pulled
po = [r["pull_off"] for r in full if not [b for b in r["buys"] if b["cls"] == "OUTSIDE" and (b["from"] or "")[:10] not in WL]]
out["no_outside"] = {"n": len(po), "pulled<=45": sum(1 for x in po if x is not None and x <= 45), "pulled<=100": sum(1 for x in po if x is not None and x <= 100),
                     "pulled<=400": sum(1 for x in po if x is not None and x <= 400)}
print("pools with no outside buy:", out["no_outside"])
# the whitelisted wallet
wl = [(r["pull_off"] - b["off"]) if r["pull_off"] is not None else None for r in full for b in r["buys"][:999] if (b["from"] or "")[:10] in WL][:2000]
out["whitelisted_0x93b07902"] = {"buys": len(wl), "pull_within_20": sum(1 for x in wl if x is not None and 0 <= x <= 20)}
print("0x93b07902:", out["whitelisted_0x93b07902"])
# outside wallets
ow = collections.Counter((b["from"] or "")[:10] for r in full for b in r["buys"] if b["cls"] == "OUTSIDE")
out["outside_wallets"] = ow.most_common(20)
json.dump(out, open(os.path.join(HERE, "reaction_cdf.json"), "w"), indent=1)
