"""The report's tables: Q1 per 6-hour period; Q2 the reaction by pool class; the decoys over time, their position against our buy, the
count per pool in the evening of Oct 11; the bot's first-buy size by class."""
import json, pickle, collections, time, statistics as st
from xcommon import *
D = pickle.load(open("x02_pools.pkl", "rb")); pools = D["pools"]; P = {p["pid"]: p for p in pools}
X3 = json.load(open("x03_rows.json"))
R65 = "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc"; RFD = "0xfd1b271f235e5230eaee9d914ccb1af495bfb758"
def pc(v, q):
    v = sorted(v); return v[min(len(v) - 1, int(q * len(v)))] if v else None
def d3(v, f="{:.0f}"): return "/".join(f.format(x) for x in (pc(v, .1), pc(v, .5), pc(v, .9))) if v else "-"
def pkey(s): return (s[3:5], s[6:])
print("## Q1. Our trades on 2.433, per 6-hour period")
print("| period | trades | stake ETH (n) | buy at +1/+2/+3 | T p10/50/90 | sell, blocks after buy p10/50/90 | sell vs T: before / T+0 / T+1 / T+2 / T+3+ / none | return mean / median | pull <= T+3 | no pull by T+60 | net $ |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for per in sorted(set(r["period"] for r in X3), key=pkey):
    v = [r for r in X3 if r["period"] == per and r["line"] == "2.433"]
    if not v: continue
    sk = collections.Counter(round(r["eth_in"] / 1e18, 4) for r in v).most_common(3)
    bo = collections.Counter(r["buy_off"] for r in v)
    s = [r["sell_rel_T"] for r in v]
    cnt = (sum(1 for x in s if x is not None and x < 0), s.count(0), s.count(1), s.count(2), sum(1 for x in s if x is not None and x >= 3), s.count(None))
    rets = [100 * r["ret"] for r in v if r["ret"] is not None]
    p3 = sum(1 for r in v if r["pull_rel_T"] is not None and r["pull_rel_T"] <= 3); np60 = sum(1 for r in v if r["T"] is not None and (r["pull_rel_T"] is None or r["pull_rel_T"] > 60))
    usd = sum(((r["eth_out"] or 0) - r["eth_in"]) / 1e18 * USD for r in v)
    print(f"| {per} | {len(v)} | {', '.join(f'{a} ({b})' for a, b in sk)} | {bo.get(1,0)}/{bo.get(2,0)}/{bo.get(3,0)} | {d3([r['T'] for r in v if r['T'] is not None])} | "
          f"{d3([r['sell_after_buy'] for r in v if r['sell_after_buy'] is not None])} | {' / '.join(map(str, cnt))} | {st.mean(rets):+.1f}% / {st.median(rets):+.1f}% | {p3} | {np60} | {usd:+.0f} |")
v = [r for r in X3 if r["line"] == "3.0"]
for r in v: print(f"\n3.0 probe: {utc(r['ts'])}, buy +{r['buy_off']} {r['eth_in']/1e18} ETH, bot never bought, pulled at +{r['pull']} ({r['pull'] - r['buy_off']} after our buy), sold at our buy + {r['sell_after_buy']}, return {100*r['ret']:.0f}%")
print("\n## Q1b. Selling sooner: the value of our tokens before T, vs right behind the bot's buy, vs the actual sell (2.433, the bot bought after our buy)")
print("| day | trades | at the end of our buy's block p50 | best block before T: p50 / p90 / max | trades where any block before T > +0.5% | right behind the bot's buy p50 | actual p50 | actual - behind T, mean |")
print("|---|---|---|---|---|---|---|---|")
for day in ("Oct10", "Oct11"):
    w = [r for r in X3 if r["line"] == "2.433" and r["period"].startswith(day) and r["path"]]
    imm = [100 * r["immediate"] for r in w]; best = [100 * r["best_pre_T"] for r in w]
    bt = [100 * r["ret_behind_T"] for r in w if r["ret_behind_T"] is not None]; act = [100 * r["ret"] for r in w if r["ret"] is not None]
    gap = [100 * (r["ret"] - r["ret_behind_T"]) for r in w if r["ret"] is not None and r["ret_behind_T"] is not None and r["sell_rel_T"] is not None and r["sell_rel_T"] >= 0]
    print(f"| {day} | {len(w)} | {pc(imm,.5):+.2f}% | {pc(best,.5):+.2f}% / {pc(best,.9):+.2f}% / {max(best):+.2f}% | {sum(1 for x in best if x > 0.5)} | {pc(bt,.5):+.1f}% | {pc(act,.5):+.1f}% | {st.mean(gap):+.2f} pts (sells at T+0..: n {len(gap)}) |")
for day in ("Oct11",):
    for k in (1, 2):
        w = [r for r in X3 if r["line"] == "2.433" and r["period"].startswith(day) and r["sell_rel_T"] == k and r["ret_behind_T"] is not None]
        print(f"  {day} sells at T+{k}: n {len(w)}, actual - right behind T: mean {st.mean([100*(r['ret']-r['ret_behind_T']) for r in w]):+.2f} pts, median {st.median([100*(r['ret']-r['ret_behind_T']) for r in w]):+.2f}")
w = [r for r in X3 if r["line"] == "2.433" and r["period"] == "Oct10 12-18"]
for lab, f in (("sold before T", lambda r: r["sell_rel_T"] is not None and r["sell_rel_T"] < 0), ("sold at T+1", lambda r: r["sell_rel_T"] == 1)):
    x = [100 * r["ret"] for r in w if f(r) and r["ret"] is not None]
    print(f"  Oct 10 12-18, {lab}: n {len(x)}, return mean {st.mean(x):+.2f}% median {st.median(x):+.2f}%")
# ---------------- Q2
def fronter_class(p):
    sw = p["sw"]; Tli = p["T_li"]
    ahead = [s for s in sw if s["buy"] and s["who"] in ("ours", "w") and (Tli is None or (s["bn"], s["li"]) < Tli) and (Tli is not None or s["off"] <= 60)]
    if any(s["who"] == "ours" for s in ahead): return "US", ahead
    big = [s for s in ahead if s["q"] >= int(0.001e18)]
    if big:
        s = big[0]; return ("D65" if s["to"] == R65 else "DFD" if s["to"] == RFD else "OTHER") + (" fresh" if (s["nonce"] or 0) <= 1 else ""), ahead
    if any(s["q"] >= int(0.00003e18) for s in ahead): return "small only", ahead
    return "nobody", ahead
print("\n## Q2. The operator's reaction, per 6-hour period and per class of pool (who bought ahead of the bot's first buy T)")
print("classes: US = our relay ahead (with or without others); D65/DFD/OTHER = no us, the first buy >= 0.001 ETH ahead was through that router ('fresh' = nonce 0/1 wallet);")
print("small only = only buys of 0.00003-0.001 ETH ahead; nobody = only dust/the sentinel. Pull within launch + 1200 blocks.")
print("| line | period | class | pools | no bot buy | pulled <= T+3 | T+4..10 | T+11..60 | not by T+60 | bot 2nd buy before the pull | bot 1st buy ETH p50 |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
rows = []
for p in pools:
    c, ahead = fronter_class(p); p["cls"] = c; p["ahead"] = ahead
for line in ("2.433", "3.0"):
    for per in sorted(set(p["period"] for p in pools), key=pkey):
        v = [p for p in pools if p["line"] == line and p["period"] == per]
        for c, n in sorted(collections.Counter(p["cls"] for p in v).items(), key=lambda kv: -kv[1]):
            w = [p for p in v if p["cls"] == c]; wt = [p for p in w if p["T"] is not None]
            k = lambda a, b: sum(1 for p in wt if p["pull"] is not None and a <= p["pull"] - p["T"] <= b)
            sec = sum(1 for p in wt if len(p["bot_buys"]) > 1 and (p["pull"] is None or p["bot_buys"][1][0] < p["pull"]))
            print(f"| {line} | {per} | {c} | {n} | {n - len(wt)} | {k(-99,3)} | {k(4,10)} | {k(11,60)} | {len(wt) - k(-99,60)} | {sec} | {pc([p['T_q']/1e18 for p in wt], .5) or 0:.3f} |")
# decoys over time
print("\n## Decoys on 2.433 by hour: pools, pools with us ahead, pools with a D65 buy >= 0.001 ahead of T (fresh wallet / recurring), with a DFD buy >= 0.001, small D65/DFD buys only")
print("| hour (UTC) | pools | ours | D65 >= 0.001 (fresh/recurring) | DFD >= 0.001 | D65/DFD < 0.001 only | in pools without us: D65/DFD >= 0.001 | sizes |")
print("|---|---|---|---|---|---|---|---|")
def hr(ts): g = time.gmtime(ts); return f"Oct{g.tm_mday} {g.tm_hour:02d}"
byh = collections.defaultdict(list)
for p in pools:
    if p["line"] == "2.433": byh[hr(p["ts"])].append(p)
for h in sorted(byh, key=lambda s: (s[3:5], s[6:])):
    v = byh[h]; ours = sum(1 for p in v if any(s["who"] == "ours" for s in p["ahead"]))
    def has(p, r, big=True): return [s for s in p["ahead"] if s["to"] == r and ((s["q"] >= int(0.001e18)) == big)]
    d65 = [p for p in v if has(p, R65)]; dfd = [p for p in v if has(p, RFD)]
    fr = sum(1 for p in d65 if any((s["nonce"] or 0) <= 1 for s in has(p, R65)))
    small = sum(1 for p in v if not has(p, R65) and not has(p, RFD) and (has(p, R65, False) or has(p, RFD, False)))
    nous = [p for p in v if not any(s["who"] == "ours" for s in p["ahead"])]
    nous_d = sum(1 for p in nous if has(p, R65) or has(p, RFD))
    sizes = collections.Counter(round(s["q"] / 1e18, 4) for p in v for s in p["ahead"] if s["to"] in (R65, RFD)).most_common(3)
    print(f"| {h} | {len(v)} | {ours} | {len(d65)} ({fr}/{len(d65)-fr}) | {len(dfd)} | {small} | {nous_d} of {len(nous)} | {sizes} |")
# position of the decoys against our buy
print("\n## Where the D65/DFD buys landed against our buy (pools with our buy ahead of T): earlier block / same block before us / same block after us / later block")
pos = collections.defaultdict(collections.Counter)
for p in pools:
    us = next((s for s in p["sw"] if s["who"] == "ours" and s["buy"]), None)
    if not us: continue
    for s in p["ahead"]:
        if s["to"] not in (R65, RFD): continue
        k = "earlier block" if s["bn"] < us["bn"] else "same block, before us" if (s["bn"] == us["bn"] and s["li"] < us["li"]) else "same block, after us" if s["bn"] == us["bn"] else "later block"
        pos[(p["period"], "big" if s["q"] >= int(0.001e18) else "small")][k] += 1
for k in sorted(pos, key=lambda k: (pkey(k[0]), k[1])): print(f"  {k[0]} {k[1]:5s}: {dict(pos[k])}")
# decoy count per pool in the evening of Oct 11 (buys of 0.0046-0.0053 ETH ahead of T by anyone but us)
print("\n## Oct 11 from 16:00: buys of 0.0046-0.0053 ETH ahead of T per pool (not ours), by 30 minutes: pools / mean count / pools with 2+ / with 1 / with 0; which routers")
b30 = collections.defaultdict(list)
for p in pools:
    pass
for p in pools:
    if p["line"] != "2.433" or p["ts"] < 1791590400 + 86400 + 16 * 3600: continue
    g = time.gmtime(p["ts"]); b30[f"{g.tm_hour:02d}:{(g.tm_min // 30) * 30:02d}"].append(p)
for k in sorted(b30):
    v = b30[k]; cnts = []
    rt = collections.Counter()
    for p in v:
        dec = [s for s in p["ahead"] if s["who"] == "w" and int(0.0046e18) <= s["q"] <= int(0.0053e18)]
        cnts.append(len(dec)); rt.update((s["to"][:10], "fresh" if (s["nonce"] or 0) <= 1 else s["eoa"][:10]) for s in dec)
    print(f"  {k}: pools {len(v):2d} (ours {sum(1 for p in v if any(s['who']=='ours' for s in p['ahead'])):2d}) mean {st.mean(cnts):.2f} | 2+: {sum(1 for c in cnts if c >= 2)} 1: {cnts.count(1)} 0: {cnts.count(0)} | {dict(rt)}")
