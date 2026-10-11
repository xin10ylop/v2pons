"""Stage 6: the operator's reaction re-measured from the chain over the last ~11.5 h of 3.0 pools (u6_pools.json): every buy in the pool that is
not the bot's (router 0x1cbaf24d c1120e3d), not the sentinel 0xe71a69f4, i.e. outside buys incl. ours; dust < 0.00003 ETH; the first pull
(ModifyLiquidity with negative delta) at or after the buy and its lag in blocks; 'before T' = the buy lands ahead of the bot's first buy (or the
bot never bought). Recurring wallets (>= 5 pools) are listed separately (the operator's own decoys are spared).
-> u6b_rows.pkl, and the pre-T lag list used by the front model (u7)."""
import json, pickle, collections, os
from lib import *
os.chdir(HERE)
D = json.load(open("u6_pools.json")); kv_tx = KV("tx")
P = []
for p in D["pools"]:
    sw, ml = [], []
    for e in p["ev"]:
        t = kv_tx.d.get(e["tx"]) or {}
        base = {"bn": e["bn"], "off": e["bn"] - p["L"], "ti": e["ti"], "tx": e["tx"], "eoa": (t.get("from") or "").lower(), "to": (t.get("to") or "").lower(),
                "sel": (t.get("input") or "")[2:10]}
        if e["kind"] == "swap":
            a0 = sgn(W(e["data"], 0)); r = dict(base, buy=a0 < 0, q=abs(a0))
            r["who"] = ("bot" if r["to"] == BOT and r["sel"] == "c1120e3d" else "sentinel" if r["eoa"] == SENTINEL else "ours" if r["eoa"] == OURS or r["to"] == RELAY else "outside")
            sw.append(r)
        else: ml.append(dict(base, dL=sgn(W(e["data"], 2))))
    bots = [s for s in sw if s["who"] == "bot" and s["buy"]]
    P.append(dict(pid=p["pid"], L=p["L"], span=p["span"], sw=sw, ml=ml, Tbn=bots[0]["bn"] if bots else None, Tti=bots[0]["ti"] if bots else None,
                  T=bots[0]["off"] if bots else None, pull=next((m["off"] for m in ml if m["dL"] < 0), None)))
wallet_pools = collections.Counter()
for p in P:
    for w in {s["eoa"] for s in p["sw"] if s["who"] in ("outside", "ours") and s["buy"]}: wallet_pools[w] += 1
rows = []
for p in P:
    for s in p["sw"]:
        if s["who"] not in ("outside", "ours") or not s["buy"]: continue
        nxt = [m["bn"] for m in p["ml"] if m["dL"] < 0 and m["bn"] >= s["bn"]]
        before = p["Tbn"] is None or s["bn"] < p["Tbn"] or (s["bn"] == p["Tbn"] and s["ti"] < p["Tti"])
        rows.append(dict(pid=p["pid"], L=p["L"], off=s["off"], T=p["T"], eth=s["q"] / 1e18, eoa=s["eoa"], to=s["to"], who=s["who"], before=before,
                         lag=nxt[0] - s["bn"] if nxt else None, left=p["L"] + p["span"] - s["bn"], dust=s["q"] < 3 * 10 ** 13, recurring=wallet_pools[s["eoa"]] >= 5))
pickle.dump({"rows": rows, "pools": [{k: v for k, v in p.items() if k not in ("sw", "ml")} for p in P]}, open("u6b_rows.pkl", "wb"))
ts0 = D["head_ts"] - (D["head"] - P[0]["L"]) / D["bps"]
print(f"pools {len(P)} launched {utc(ts0)} .. {utc(D['head_ts'] - (D['head'] - P[-1]['L']) / D['bps'])} UTC; with T {sum(1 for p in P if p['T'] is not None)}; "
      f"no bot buy {sum(1 for p in P if p['T'] is None)}; pulled {sum(1 for p in P if p['pull'] is not None)}")
print("recurring outside wallets (>= 5 pools):", [(w[:10], n) for w, n in wallet_pools.most_common() if n >= 5])
for lab, f in (("BEFORE T (or no bot buy)", lambda r: r["before"]), ("AFTER T", lambda r: not r["before"])):
    print(f"\n== outside buys {lab}")
    for r in sorted([r for r in rows if f(r)], key=lambda r: r["L"]):
        print(f"  {utc(D['head_ts'] - (D['head'] - r['L']) / D['bps'])} pool {r['pid'][:10]} {r['who']:7s} {r['eoa'][:10]} via {r['to'][:10]} {r['eth']:.6f} at L+{r['off']:<3d} T {str(r['T']):>4} "
              f"{'dust' if r['dust'] else '    '} {'recurring' if r['recurring'] else '         '} pull lag {str(r['lag']):>4} (history after {r['left']})")
    nd = [r for r in rows if f(r) and not r["dust"] and not r["recurring"]]
    first = {}
    for r in sorted(nd, key=lambda r: r["off"]): first.setdefault(r["pid"], r)
    lags = sorted(r["lag"] for r in first.values() if r["lag"] is not None)
    print(f"  non-dust one-off buys {len(nd)} in {len(first)} pools; first per pool pulled at all {len(lags)}, within 30 blocks {sum(1 for l in lags if l <= 30)}; lags {lags}; "
          f"min {lags[0] if lags else None} median {pct(lags, .5) if lags else None}")
