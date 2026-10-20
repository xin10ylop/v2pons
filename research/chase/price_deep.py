#!/usr/bin/env python3
"""price_deep.py rh_deep.json: the operator's new pools priced: cadence, liquidity, bot timing, pull timing, who buys, and the paper
return of (A) the early seat: buy at launch+2, sell into the bot (first buy + h) and (B) the flip: buy at first buy + 2, sell + 7."""
import json, os, sys, statistics as st, collections, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src")); import v4math
d = json.load(open(sys.argv[1])); pools, ev, txs = d["pools"], d["events"], d["txs"]
BT = float(sys.argv[2]) if len(sys.argv) > 2 else 0.1; GAS_USD = float(sys.argv[3]) if len(sys.argv) > 3 else 0.02; ETH_USD = 2570.0; STAKE_A = float(sys.argv[4]) if len(sys.argv) > 4 else 0.02
def state_after(sw, bn, sp0, L0):
    prev = [x for x in sw if x[0] <= bn]; return (prev[-1][4], prev[-1][5]) if prev else (sp0, L0)
def ret(sw, pull, sp0, L0, fee, entry_bn, exit_bn, stake):
    f = fee/1e6; sp, L = state_after(sw, entry_bn, sp0, L0)
    if L == 0: return None
    tok = v4math.buy_out(sp, L, stake*(1-f))
    if tok <= 0: return None
    if pull is not None and pull <= exit_bn: return -1.0
    sp2, L2 = state_after(sw, exit_bn, sp0, L0)
    if L2 == 0: return -1.0
    return (v4math.sell_out(sp2, L2, tok)*(1-f) - stake)/stake - GAS_USD/(stake/1e18*ETH_USD)
# operator wallets: senders seen on >= 3 pools
wallet_pools = collections.defaultdict(set)
for pid, e in ev.items():
    for s in e["swaps"]:
        t = txs.get(s[6])
        if t: wallet_pools[t[0]].add(pid)
op_wallets = {w for w, ps in wallet_pools.items() if len(ps) >= 3}
print(f"pools {len(pools)}; swap wallets {len(wallet_pools)}, recurring (>=3 pools) {len(op_wallets)}, single-pool {sum(1 for ps in wallet_pools.values() if len(ps)==1)}")
rows = []; days = collections.Counter(); fees = collections.Counter()
for pid in sorted(pools, key=lambda k: pools[k]["bn"]):
    p = pools[pid]; e = ev.get(pid)
    if not e: continue
    b0 = p["bn"]; sw = e["swaps"]; liq = e["liq"]
    adds = [l for l in liq if l[3] > 0]; rems = [l for l in liq if l[3] < 0]
    L0 = v4math.active_liquidity(p["tick0"], [(l[1], l[2], l[3]) for l in adds if l[0] <= b0]) if adds else 0
    if adds:
        L, tl, tu = adds[0][3], adds[0][1], adds[0][2]; sp = p["sqrtP0"]/2**96; spl, spu = 1.0001**(tl/2), 1.0001**(tu/2); spc = min(max(sp, spl), spu)
        eth0 = L*(spu-spc)/(spc*spu)/1e18 if spu > spc else 0.0
    else: eth0 = 0.0
    pull = rems[0][0] if rems else None
    buys = [s for s in sw if s[2] < 0]; sells = [s for s in sw if s[2] > 0]
    real = [s for s in buys if -s[2] >= 0.0002e18]
    first = real[0][0] if real else None
    buyers = collections.Counter(); outside = []
    for s in buys:
        t = txs.get(s[6])
        if t:
            buyers[t[0]] += 1
            if t[0] not in op_wallets: outside.append((s[0]-b0, -s[2]/1e18, t[2]))
    r = {"bn": b0, "fee": p["fee"], "eth0": eth0, "pull": (pull-b0) if pull else None, "first": (first-b0) if first else None, "nbuys": len(buys), "nsells": len(sells),
         "eth_bought": sum(-s[2] for s in buys)/1e18, "buyers": len(buyers), "outside": outside[:5], "n_outside": len(outside)}
    fees[p["fee"]] += 1
    for stake_name, stake in (("20m", int(STAKE_A*1e18)), ("1.2m", int(0.0012e18))):
        r["A_" + stake_name] = {h: ret(sw, pull, p["sqrtP0"], L0, p["fee"], b0+2, (first if first else b0+int(8/BT))+h, stake) for h in (2, 5, 10, 20, 50)}
        r["A_" + stake_name].update({"t%d" % n: ret(sw, pull, p["sqrtP0"], L0, p["fee"], b0+2, b0+n, stake) for n in (50, 100, 200, 300, 600)})
        r["B_" + stake_name] = ret(sw, pull, p["sqrtP0"], L0, p["fee"], first+2, first+2+7, stake) if first else None
    rows.append(r)
print("fees:", fees.most_common(8))
print("liquidity ETH: median %.3f, p10 %.3f, p90 %.3f; last 20 median %.3f" % (st.median([r["eth0"] for r in rows]), sorted(r["eth0"] for r in rows)[len(rows)//10], sorted(r["eth0"] for r in rows)[len(rows)*9//10], st.median([r["eth0"] for r in rows[-20:]])))
fb = [r["first"] for r in rows if r["first"] is not None]; pl = [r["pull"] for r in rows if r["pull"] is not None]
print(f"first real buy: on {len(fb)}/{len(rows)} pools, offset blocks p10/50/90 = {sorted(fb)[len(fb)//10]}/{int(st.median(fb))}/{sorted(fb)[len(fb)*9//10]}  ({st.median(fb)*BT:.1f} s)")
print(f"pull inside 5 min: {len(pl)}/{len(rows)}, offset blocks p10/50/90 = {sorted(pl)[len(pl)//10]}/{int(st.median(pl))}/{sorted(pl)[len(pl)*9//10]} ({st.median(pl)*BT:.0f} s); pulls before the first buy: {sum(1 for r in rows if r['pull'] is not None and (r['first'] is None or r['pull'] < r['first']))}")
print(f"buys per pool median {st.median([r['nbuys'] for r in rows])}, ETH bought median {st.median([r['eth_bought'] for r in rows]):.3f}, buyers median {st.median([r['buyers'] for r in rows])}, pools with an outside buyer {sum(1 for r in rows if r['n_outside'])}")
def summ(vals):
    v = [x for x in vals if x is not None]
    return f"n={len(v)} mean {100*st.mean(v):+.1f}% median {100*st.median(v):+.1f}% win {100*sum(1 for x in v if x>0)/len(v):.0f}% pulled {sum(1 for x in v if x<=-0.99)}" if v else "n=0"
for stake_name in ("20m", "1.2m"):
    print(f"\n== stake {'0.02' if stake_name=='20m' else '0.0012'} ETH")
    for h in (2, 5, 10, 20, 50): print(f"  A early seat (launch+2 -> first buy+{h:>2}): {summ([r['A_'+stake_name][h] for r in rows])}")
    for n in ("t50", "t100", "t200", "t300", "t600"): print(f"  A early seat (launch+2 -> launch+{n[1:]:>3}): {summ([r['A_'+stake_name][n] for r in rows])}")
    print(f"  B flip (first buy+2 -> +7):            {summ([r['B_'+stake_name] for r in rows])}")
# by day
byday = collections.defaultdict(list)
for r in rows: byday[r["bn"]//int(86400/BT)].append(r)   # ~1 day of 0.1 s blocks, relative buckets
print("\nper ~day bucket (launches, median liq, pulled<5min, early seat first+10 mean, flip mean):")
for k in sorted(byday):
    rs = byday[k]; a = [r["A_20m"][10] for r in rs if r["A_20m"][10] is not None]; b = [r["B_20m"] for r in rs if r["B_20m"] is not None]
    print(f"  blocks {rs[0]['bn']}..{rs[-1]['bn']}: {len(rs):4d} launches, liq {st.median([r['eth0'] for r in rs]):.2f}, pulled {sum(1 for r in rs if r['pull'] is not None)}, A {100*st.mean(a) if a else 0:+.1f}%, B {100*st.mean(b) if b else 0:+.1f}%")
print("\nlast 8 pools:")
for r in rows[-8:]: print("  ", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k in ("bn", "fee", "eth0", "first", "pull", "nbuys", "eth_bought", "buyers", "n_outside")}, "A10 %s B %s" % (None if r["A_20m"][10] is None else round(100*r["A_20m"][10], 1), None if r["B_20m"] is None else round(100*r["B_20m"], 1)))
json.dump(rows, open(sys.argv[1].replace(".json", "_priced.json"), "w"))
