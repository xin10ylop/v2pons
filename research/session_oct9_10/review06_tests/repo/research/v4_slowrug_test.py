#!/usr/bin/env python3
"""Report 24.45's pending test, run on the chain: the 2-2.45% fee v4 launch family on Robinhood Chain, followed by its operator
(the launcher contract 0x3194e326, a fresh deployer per launch), Sep 29 21:00 - Oct 8 10:30 UTC, from v4_slowrug_pull.py's data
(the 1.5-5% fee band, and the operator's launches outside it).

The question 24.45 left open: when an outsider buys before the operator's scripted crowd, does the crowd still come, or does the
operator withhold it and pull the liquidity? The live answer was to be five to ten $3 buys at the first seat. Every swap's wallet
is known here, so the same experiment is read from other people's buys. Roles per swap, per launcher:
  dep    the launch transaction's sender
  fresh  a wallet whose nonce at its first swap on this launch is <= 2 (the operator's single-use wallets)
  wash   a wallet that trades only this launcher's launches in the data, on 4 or more of them, round-tripping (3 or more swaps a
         launch on average): the recurring volume fleet
  dust   any other wallet's buy under 0.0002 ETH (test buys; the busiest tester, 0xb4d43149, kept trading after the operator paused)
  out    everyone else: an established outside wallet
The seat: a $3 buy at the head of block b0+1 (the pool state after the launch block), priced with exact single-range v4 math
against the pool's real liquidity, sold after a fixed hold at the pool's real state; a liquidity removal before the sell is -100%.

    python3 src/analysis/v4_slowrug_test.py data/derived/edge_check/Q/slowrug.json.gz data/derived/edge_check/Q/slowrug_op.json.gz \\
        > data/derived/edge_check/Q/slowrug_test.txt
"""
import json, sys, time, gzip, random, collections, statistics as st, urllib.request
ld = lambda f: json.load(gzip.open(f) if f.endswith(".gz") else open(f))
P, S, L, T, TS = {}, {}, {}, {}, {}; WINDOW = None
for f in sys.argv[1:]:
    d = ld(f); WINDOW = WINDOW or d["window"]
    P.update(d["pools"]); S.update(d["swaps"]); L.update(d["liquidity"]); T.update(d["txs"]); TS.update({int(k): v for k, v in d.get("launch_ts", {}).items()})
missing = sorted({p["bn"] for p in P.values()} - set(TS))
for i in range(0, len(missing), 50):                            # launch timestamps a data file did not carry
    req = urllib.request.Request("https://rpc.mainnet.chain.robinhood.com", json.dumps([{"jsonrpc": "2.0", "id": j, "method": "eth_getBlockByNumber", "params": [hex(b), False]}
          for j, b in enumerate(missing[i:i+50])]).encode(), {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"})
    for k in range(8):
        try: res = json.load(urllib.request.urlopen(req, timeout=60)); break
        except Exception: time.sleep(4 * (k + 1))
    for x in res: TS[int(x["result"]["number"], 16)] = int(x["result"]["timestamp"], 16)
ETHUSD, STAKE, GAS = 2570.0, 3.0, 0.02; X = STAKE / ETHUSD * 1e18; Q = 2 ** 96; HOLDS = (50, 100, 200, 300)   # blocks (~0.1 s)
OP = "3194e32622c5d860a0572c74edda99dcfd8fc827"
launcher = {pid: T.get(p["tx"], ["", ""])[1] for pid, p in P.items()}
deployer = {pid: T.get(p["tx"], [""])[0] for pid, p in P.items()}
day = lambda pid: time.strftime("%m-%d", time.gmtime(TS[P[pid]["bn"]]))
med = lambda v: st.median(v) if v else float("nan")
pct = lambda v, qs: [sorted(v)[int(q * (len(v) - 1))] for q in qs] if v else []
tier = lambda f: "2-2.45%" if 20000 <= f <= 24500 else ("1.5-5% other" if 15000 <= f <= 50000 else ("< 1%" if f < 10000 else "other"))

seen_on = collections.defaultdict(lambda: collections.defaultdict(set)); n_swaps = collections.Counter()
for pid, sw in S.items():
    for x in sw: seen_on[T[x[8]][0]][launcher[pid]].add(pid); n_swaps[T[x[8]][0]] += 1
def roles(pid):
    lz = launcher[pid]; first_nonce = {}; out = []
    for x in sorted(S.get(pid, []), key=lambda x: (x[0], x[1])):
        t = T[x[8]]; w = t[0]; first_nonce.setdefault(w, t[2]); so = seen_on[w]
        if w == deployer[pid]: r = "dep"
        elif first_nonce[w] <= 2: r = "fresh"
        elif len(so[lz]) >= 4 and len(so) == 1 and n_swaps[w] >= 3 * len(so[lz]): r = "wash"
        elif x[3] < 0 and -x[3] < 2e14: r = "dust"
        else: r = "out"
        out.append((x, r, w, t))
    return out

def buy(sp, Lq, x):                                   # ETH is currency0: 1/s' = 1/s + x/L; tokens out = L (s - s')
    s = sp / Q
    if Lq <= 0 or s <= 0: return 0.0
    s2 = 1.0 / (1.0 / s + x / Lq); return Lq * (s - s2)
def sell(sp, Lq, t):                                  # tokens in: s' = s + t/L; ETH out = L (1/s - 1/s')
    s = sp / Q
    if Lq <= 0 or s <= 0 or t <= 0: return 0.0
    s2 = s + t / Lq; return Lq * (1.0 / s - 1.0 / s2)
def state(pid, bn_last):
    sw = [x for x in S.get(pid, []) if x[0] <= bn_last]
    if sw: return max(sw, key=lambda x: (x[0], x[1]))[5:7]
    p = P[pid]; adds = [x for x in L.get(pid, []) if x[5] > 0 and x[0] <= bn_last and x[3] < p["tick0"] <= x[4]]   # a buy moves the price down
    return p["sqrtP0"], sum(x[5] for x in adds)

def launch_row(pid):
    p = P[pid]; b0 = p["bn"]; R = roles(pid)
    buys = [(x[0] - b0, r, -x[3] / 1e18, w) for x, r, w, t in R if x[3] < 0]
    crowd = [b for b in buys if b[1] in ("fresh", "wash") and b[2] >= 2e-4]; outs = [b for b in buys if b[1] == "out"]
    rem = sorted(x[0] - b0 for x in L.get(pid, []) if x[5] < 0)
    row = {"pid": pid, "day": day(pid), "fee": p["fee"], "crowd_first": crowd[0][0] if crowd else None, "crowd_n": len(crowd),
           "crowd30": sum(1 for b in crowd if b[0] <= 300), "eth30": sum(b[2] for b in crowd if b[0] <= 300), "out": outs,
           "nonop": [b for b in buys if b[1] in ("out", "dust")], "pull": rem[0] if rem else None,
           "pull_by_dep": bool(rem) and T[min((x for x in L[pid] if x[5] < 0), key=lambda x: (x[0], x[1]))[6]][0] == deployer[pid],
           "roles": collections.Counter(r for _, r, _, _ in R)}
    pnl = collections.defaultdict(lambda: [0.0, 0.0])          # each outsider's ETH in / out on this launch
    for x, r, w, t in R:
        if r == "out" or (r == "dust" and x[3] < 0): pnl[w][0 if x[3] < 0 else 1] += abs(x[3]) / 1e18
    row["out_pnl"] = {w: v for w, v in pnl.items() if v[0] >= 2e-4}
    sp, Lq = state(pid, b0); fee = p["fee"] / 1e6; tok = buy(sp, Lq, X * (1 - fee)); row["seat"] = {}
    if tok <= 0: return row
    for h in HOLDS:
        ex = b0 + 1 + h
        if row["pull"] is not None and b0 + row["pull"] <= ex: row["seat"][h] = -1.0 - GAS / STAKE
        else:
            sp2, L2 = state(pid, ex); row["seat"][h] = (sell(sp2, L2, tok) * (1 - fee) - X) / X - GAS / STAKE
    return row

rows = {pid: launch_row(pid) for pid in P}
groups = collections.defaultdict(list)
for pid in P: groups[launcher[pid]].append(pid)
top = [lz for lz, _ in sorted(groups.items(), key=lambda g: -len(g[1]))[:5]]
ops = sorted(groups[OP], key=lambda p: P[p]["bn"]); opr = [rows[p] for p in ops]
print(f"window {WINDOW[0]} - {WINDOW[1]} UTC; {len(P)} launches (no-hook, tick 200, ETH: the 1.5-5% fee band and the operator's launches "
      f"outside it); stake ${STAKE:.0f} at ${ETHUSD:.0f}/ETH\n")

print("1. SUPPLY: launches per UTC day by launcher")
days = sorted({r["day"] for r in rows.values()})
print(f"   {'launcher':12s} {'n':>4s} " + " ".join(f"{d[3:]:>4s}" for d in days) + "  fees")
for lz in top:
    ps = groups[lz]; c = collections.Counter(rows[p]["day"] for p in ps); f = collections.Counter(P[p]["fee"] for p in ps)
    print(f"   0x{lz[:10]} {len(ps):4d} " + " ".join(f"{c.get(d, 0):4d}" for d in days) + "  " + ", ".join(f"{k/1e4:g}%:{v}" for k, v in f.most_common(5)))
print(f"   the operator 0x{OP[:10]} by fee tier and day:")
for tr in ("2-2.45%", "1.5-5% other", "< 1%", "other"):
    c = collections.Counter(r["day"] for r in opr if tier(r["fee"]) == tr)
    if c: print(f"      {tr:13s} " + " ".join(f"{c.get(d, 0):4d}" for d in days))
print(f"   (Sep 27-29, report 24.45: 107-126 launches a day, 80% of them at 2.45%)")

print("\n2. ANATOMY (blocks are ~0.1 s; crowd = fresh + wash wallets, real size)")
for lz in top:
    rs = [rows[p] for p in groups[lz]]; rc = sum((r["roles"] for r in rs), collections.Counter()); n = sum(rc.values()) or 1
    withc = [r for r in rs if r["crowd_n"] >= 3]; pulls = [r["pull"] for r in rs if r["pull"] is not None]
    print(f"   0x{lz[:10]} n={len(rs)}: swaps by role " + ", ".join(f"{k} {v/n:.0%}" for k, v in rc.most_common()) +
          f"; a crowd on {len(withc)}; its first buy at blk p10/50/90 {pct([r['crowd_first'] for r in withc], (.1, .5, .9))}; "
          f"crowd buys in 30 s {med([r['crowd30'] for r in withc]):.0f} ({med([r['eth30'] for r in withc]):.2f} ETH); "
          f"pulled in 20 min {len(pulls)/len(rs):.0%}, at blk p10/50/90 {pct(pulls, (.1, .5, .9))}")

print("\n3. THE TEST, part 1: an established outside wallet's real buy (>= 0.0002 ETH) before the operator's crowd")
ex = [r for r in opr if r["out"] and (r["crowd_first"] is None or r["out"][0][0] < r["crowd_first"])]
anyo = [r for r in opr if r["out"]]
print(f"   the operator's {len(opr)} launches: an outsider bought real size on {len(anyo)}, first at blk p10/50/90 "
      f"{pct([r['out'][0][0] for r in anyo], (.1, .5, .9))}; before the crowd on {len(ex)}:")
for r in ex:
    o = r["out"][0]
    print(f"      {r['pid'][:12]} {r['day']} fee {r['fee']/1e4:g}%: 0x{o[3][:10]} bought {o[2]:.4f} ETH at +{o[0]} | crowd first "
          f"{r['crowd_first']}, {r['crowd_n']} crowd buys | pull {r['pull']}")
print("   (none is a clean case: see the report; the outsiders who bought at all came a minute or more in, behind the crowd)")

print("\n3b. THE TEST, part 2: the pull's reflex. Every non-operator buy (out or dust) on the operator's launches: does the deployer's")
print("    liquidity removal follow it within 1 s (10 blocks) or 3 s (30 blocks)? By fee tier: 2-5% (to Oct 5) and under 1% (from Oct 5)")
bins = [0, 2e-4, 1e-3, 2e-3, 5e-3, 1e-2, 10]
print(f"   {sum(1 for r in opr if r['pull'] is not None)} pulls in 20 min, sent by the launch's deployer: {sum(1 for r in opr if r['pull'] is not None and r['pull_by_dep'])}")
for name, sel in (("2-5% tiers", lambda r: r["fee"] >= 10000), ("< 1% tier", lambda r: r["fee"] < 10000)):
    rs = [r for r in opr if sel(r)]; hit = collections.defaultdict(lambda: [0, 0, 0]); lastgap = collections.Counter()
    for r in rs:
        if r["pull"] is not None:
            prior = [b for b in r["nonop"] if b[0] <= r["pull"]]
            if prior: g = r["pull"] - prior[-1][0]; lastgap[g if g <= 30 else ">30"] += 1
        for b in r["nonop"]:
            k = next(i for i in range(len(bins) - 1) if bins[i] <= b[2] < bins[i + 1]); g = (r["pull"] - b[0]) if r["pull"] is not None and r["pull"] >= b[0] else None
            hit[k][0] += 1; hit[k][1] += g is not None and g <= 10; hit[k][2] += g is not None and g <= 30
    anyo = [r for r in rs if r["out"]]; gaps = [r["pull"] - r["out"][0][0] for r in anyo if r["pull"] is not None and r["pull"] >= r["out"][0][0]]
    print(f"   {name}: {len(rs)} launches; gap from the last non-operator buy to the pull, blocks: " + ", ".join(f"{k}: {v}" for k, v in sorted(lastgap.items(), key=lambda x: (isinstance(x[0], str), x[0]))))
    for k in sorted(hit):
        n, a, b = hit[k]
        print(f"      buys of {bins[k]:.4f}-{bins[k+1]:.4f} ETH (${bins[k]*ETHUSD:.2f}-{bins[k+1]*ETHUSD:.2f}): n {n:4d}, pulled within 1 s {a/n:4.0%}, within 3 s {b/n:4.0%}")
    print(f"      first outsider buy -> pull within 5 s: {sum(1 for g in gaps if g <= 50)} of {len(anyo)} launches")
random.seed(0); anyo = [r for r in opr if r["out"]]; arr = [r["out"][0][0] for r in anyo]
gaps = [r["pull"] - r["out"][0][0] for r in anyo if r["pull"] is not None and r["pull"] >= r["out"][0][0]]
pg = [r["pull"] - a for _ in range(200) for r in opr if not r["out"] and r["crowd_n"] >= 3 and r["pull"] is not None for a in [random.choice(arr)] if r["pull"] >= a]
share = lambda n, d: n / d if d else float("nan")
print(f"   both tiers: first outsider buy -> pull within 5 s on {share(sum(1 for g in gaps if g <= 50), len(anyo)):.0%} of {len(anyo)} launches; placebo (launches with no "
      f"outsider, an arrival time drawn from the outsiders'): {share(sum(1 for g in pg if g <= 50), len(pg)):.1%}")
print("\n4. WHAT THE REAL OUTSIDERS GOT (every established wallet that bought >= 0.0002 ETH; tokens left at the pull = 0)")
for lz in top:
    v = [w for p in groups[lz] for w in rows[p]["out_pnl"].values()]
    if not v: continue
    tr = [(b - a) / a for a, b in v]
    print(f"   0x{lz[:10]}: {len(tr)} outsider positions, mean {st.mean(tr):+.1%}, median {med(tr):+.1%}, win {sum(1 for t in tr if t > 0)/len(tr):.0%}, "
          f"lost everything {sum(1 for t in tr if t <= -0.99)}; net {sum(b - a for a, b in v):+.3f} ETH on {sum(a for a, b in v):.3f} ETH in")

print(f"\n5. THE ${STAKE:.0f} FIRST SEAT (head of b0+1) ON PAPER: as if the crowd comes and the pull keeps its schedule regardless of us")
for lz in top:
    rs = [rows[p] for p in groups[lz] if rows[p]["seat"]]
    if not rs: continue
    line = f"   0x{lz[:10]} n={len(rs):3d}"
    for h in HOLDS:
        v = [r["seat"][h] for r in rs]
        line += f" | {h/10:g} s: mean {st.mean(v):+.1%} med {med(v):+.1%} win {sum(1 for a in v if a > 0)/len(v):.0%}"
    print(line)
for tr in ("2-2.45%", "1.5-5% other", "< 1%"):
    for d in days:
        v = [r["seat"][200] for r in opr if r["seat"] and tier(r["fee"]) == tr and r["day"] == d]
        if v: print(f"      operator, {tr:13s} {d}: n {len(v):3d}, hold 20 s mean {st.mean(v):+.1%} median {med(v):+.1%} win {sum(1 for a in v if a > 0)/len(v):.0%}")
print("   With the reflex of 3b (a $2.6-5 buy pulled within 3 s on 74% of the 2-5% launches and 44% of the < 1% ones, a $5-13 buy on 94%")
print("   and 100%), the pull lands before a 10-30 s exit at least that often; on the paper's 20 s mean:")
v = [r["seat"][200] for r in opr if r["seat"]] or [float("nan")]
for p_pull in (0.44, 0.74, 0.94):
    print(f"      P(pull) {p_pull:.0%}: expected return at hold 20 s <= {p_pull:.2f} x (-100%) + {1-p_pull:.2f} x {st.mean(v):+.1%} = {p_pull*-1 + (1-p_pull)*st.mean(v):+.1%}")
print("\n6. A VARIANT THE CHAIN CANNOT TEST: follow the crowd and leave before the reflex (the < 1% tier, from Oct 5)")
print("   trigger: the first buy >= 0.0002 ETH by anyone (no wallet list); our buy lands 2 blocks after it; sold k blocks after our buy;")
print("   the schedule's own pulls count, a pull our buy would trigger does not (the tier's reflex is 10-19 blocks)")
low = [p for p in ops if P[p]["fee"] < 10000]
def first_real(pid):
    b0 = P[pid]["bn"]; bs = [x for x in sorted(S.get(pid, []), key=lambda x: (x[0], x[1])) if x[3] < 0 and -x[3] >= 2e14 and x[0] > b0]
    return (bs[0][0] - b0) if bs else None
fr = {p: first_real(p) for p in low}
print(f"   {len(low)} launches; the first real-size buy is the operator's crowd on {sum(1 for p in low if fr[p] is not None and fr[p] == rows[p]['crowd_first'])}")
for k in (4, 9):
    for stake in (3.0, 25.0):
        xi = stake / ETHUSD * 1e18; v = []; byd = collections.defaultdict(list)
        for p in low:
            if fr[p] is None: continue
            e = P[p]["bn"] + fr[p] + 1; f = P[p]["fee"] / 1e6; sp, Lq = state(p, e); tok = buy(sp, Lq, xi * (1 - f))
            if tok <= 0: continue
            if rows[p]["pull"] is not None and P[p]["bn"] + rows[p]["pull"] <= e + 1 + k: r = -1 - GAS / stake
            else: sp2, L2 = state(p, e + 1 + k); r = (sell(sp2, L2, tok) * (1 - f) - xi) / xi - GAS / stake
            v.append(r); byd[rows[p]["day"]].append(r)
        if not v: continue
        print(f"   sell {k} blocks after, ${stake:.0f}: n {len(v)}, mean {st.mean(v):+.1%}, median {med(v):+.1%}, win {sum(1 for a in v if a > 0)/len(v):.0%}, "
              f"p5 {pct(v, (.05,))[0]:+.1%} | by day " + " ".join(f"{d[3:]} {st.mean(x):+.1%} ({len(x)})" for d, x in sorted(byd.items())))
inwin = collections.Counter()
for p in low:
    if fr[p] is None: continue
    e = P[p]["bn"] + fr[p] + 2
    for x, r, w, t in roles(p):
        if e <= x[0] <= e + 9 and x[3] < 0: inwin[r] += 1
print("   buys landing inside the hold (our block .. +9), by role: " + ", ".join(f"{k} {v}" for k, v in inwin.most_common()))
hi = [p for p in ops if P[p]["fee"] >= 10000 and rows[p]["crowd_first"]]
for land in (1, 2, 3):
    v = []
    for p in hi:
        e = P[p]["bn"] + rows[p]["crowd_first"] + land - 1; f = P[p]["fee"] / 1e6; sp, Lq = state(p, e); tok = buy(sp, Lq, X * (1 - f))
        if tok <= 0: continue
        if rows[p]["pull"] is not None and P[p]["bn"] + rows[p]["pull"] <= e + 5: v.append(-1 - GAS / STAKE); continue
        sp2, L2 = state(p, e + 5); v.append((sell(sp2, L2, tok) * (1 - f) - X) / X - GAS / STAKE)
    if v: print(f"   the same in the 2-5% tiers (land {land} after the crowd's first buy, sell 4 blocks later): n {len(v)}, mean {st.mean(v):+.1%}, median {med(v):+.1%}")
json.dump({pid: {k: v for k, v in r.items() if k not in ("roles", "nonop")} for pid, r in rows.items()},
          open(sys.argv[1].replace(".json.gz", "").replace(".json", "") + "_rows.json", "w"))
