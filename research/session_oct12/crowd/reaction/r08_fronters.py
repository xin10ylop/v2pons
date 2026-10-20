"""(4) who fronts these launches: wallets (tx.from, class 'other') whose first buy in a pool lands at + 1..+ 5, in 3 pools or more. Per
wallet: pools, offsets, ETH per buy, the contract used, how much it sold and when (relative to the crowd's first real buy), realized
returns per closed position (sold >= 95% of its tokens, or pulled with tokens left = those lost), and the crowd and pull in its pools.
Positions still open at + 3000 (no pull) are left out of the returns. Also the ETH bought ahead of a + 2 buy (blocks + 0..+ 1, and + 2
before us) and what it does to our entry."""
from rlib import *
import collections
P = load()
pos = collections.defaultdict(list)
for p in P:
    W = collections.defaultdict(lambda: {"b": [], "s": []})
    for s in p["sw"]:
        if s["k"] == "other" and s["from"]: W[s["from"]]["b" if s["dq"] > 0 else "s"].append(s)
    for w, d in W.items():
        if not d["b"]: continue
        f0 = d["b"][0]["off"]
        tin = -sum(b["dt"] for b in d["b"]); tout = sum(s["dt"] for s in d["s"]); ein = sum(b["dq"] for b in d["b"]) / 1e18; eout = -sum(s["dq"] for s in d["s"]) / 1e18
        if tin and tout > tin * 1.001: eout *= tin / tout; tout = tin   # sold more than the buys seen (a later buy's tx not fetched): count the seen buys' share only
        frac = tout / tin if tin else 0
        closed = frac >= 0.95 or p["pull"] is not None and p["pull"] <= p["end"]
        sold_rel = [s["off"] - p["frb"] for s in d["s"]] if p["frb"] is not None else []
        pos[w].append({"pool": p["pool"], "ts": p["ts"], "first": f0, "ein": ein, "eout": eout, "frac": frac, "closed": closed, "frb": p["frb"], "pull": p["pull"],
                       "wave": p["wave"], "to": d["b"][0]["to"], "sold_rel": sold_rel, "last_sell": d["s"][-1]["off"] if d["s"] else None, "sell_off": p["sell"]})
fr = {w: v for w, v in pos.items() if sum(1 for x in v if 1 <= x["first"] <= 5) >= 3}
print(f"wallets with a first buy at +1..+5 in >= 3 pools: {len(fr)} (of {len(pos)} outside wallets); line pools {len(P)}")
print(f"{'wallet':<12} {'via':<11} {'pools':>5} {'@+1..5':>6} {'offs (top)':<22} {'ETH/buy med':>11} {'sold>=95%':>9} {'closed':>6} {'ret/pos med':>11} {'pooled ret':>10} {'pnl ETH':>9} "
      f"{'crowd came':>10} {'sold before frb':>15} {'sell vs frb med':>15} {'pulled w/ tokens':>16}")
tot = []
for w, v in sorted(fr.items(), key=lambda kv: -len(kv[1])):
    offs = collections.Counter(x["first"] for x in v).most_common(4); cl = [x for x in v if x["closed"]]
    rets = [x["eout"] / x["ein"] - 1 for x in cl if x["ein"]]
    pooled = (sum(x["eout"] for x in cl) / sum(x["ein"] for x in cl) - 1) if cl and sum(x["ein"] for x in cl) else float("nan")
    pnl = sum(x["eout"] - x["ein"] for x in cl)
    came = sum(1 for x in v if x["frb"] is not None)
    sbf = sum(1 for x in v if x["last_sell"] is not None and x["frb"] is not None and x["last_sell"] < x["frb"])
    srel = [r for x in v for r in x["sold_rel"]]
    pw = sum(1 for x in v if x["pull"] is not None and x["frac"] < 0.95)
    tot.append((w, v))
    print(f"{w[:12]:<12} {(v[0]['to'] or '')[:10]:<11} {len(v):>5} {sum(1 for x in v if 1 <= x['first'] <= 5):>6} {str(offs)[:22]:<22} {pct([x['ein'] for x in v], .5):>11.5f} "
          f"{sum(1 for x in v if x['frac'] >= 0.95):>9} {len(cl):>6} {(pct(rets, .5) or 0) * 100:>+10.1f}% {pooled * 100:>+9.1f}% {pnl:>+9.4f} {came:>10} {sbf:>15} {str(pct(srel, .5)):>15} {pw:>16}")
# ETH ahead of our + 2 buy
print("\nETH bought ahead of a + 2 buy (blocks + 0..+ 1; + 2 itself would be a same-block race), all buyers:")
ah = []; ah_nobot = []
for p in P:
    a = sum(s["dq"] for s in p["sw"] if s["off"] <= 1 and s["dq"] > 0) / 1e18; ah.append(a)
    ah_nobot.append(sum(s["dq"] for s in p["sw"] if s["off"] <= 1 and s["dq"] > 0 and not (s["from"] or "").startswith("0x776e5a2a")) / 1e18)
print(f"  pools with any: {sum(1 for a in ah if a > 0)}/{len(P)}; ETH p50/p90/max {pct(ah,.5):.5f}/{pct(ah,.9):.5f}/{max(ah):.4f}; without the +1 bot: pools {sum(1 for a in ah_nobot if a > 0)}, p90 {pct(ah_nobot,.9):.5f} max {max(ah_nobot):.4f}")
same = collections.Counter()
for p in P:
    for s in p["sw"]:
        if s["off"] == 2 and s["dq"] > 0: same[s["k"] if s["k"] != "other" else (s["from"] or "?")[:10]] += 1
print("  buys landing at + 2 (where ours would land):", same.most_common(8))
json.dump({w: v for w, v in fr.items()}, open(J("r08_fronters.json"), "w"))
# does the operator learn? For each recurring early wallet: the crowd's arrival by + 78 and the pull by + 150 in its pools, first half of
# its pools against the second half, each against all line pools launched in the same span (expected)
print("\nlearning check (per recurring early wallet with >= 10 pools): crowd by +78 and pulled <= +150 in its pools, first half / second half,"
      " against every line pool launched in the same span")
Pt = sorted(P, key=lambda p: p["ts"])
def base(t0, t1):
    g = [p for p in Pt if t0 <= p["ts"] <= t1]
    if not g: return None, None
    return sum(1 for p in g if p["frb"] is not None and p["frb"] <= 78) / len(g), sum(1 for p in g if p["pull"] is not None and p["pull"] <= 150) / len(g)
for w, v in sorted(pos.items(), key=lambda kv: -len(kv[1])):
    if len(v) < 10 or sum(1 for x in v if x["first"] <= 10) < 5: continue
    v = sorted(v, key=lambda x: x["ts"]); h = len(v) // 2; out = []
    for part in (v[:h], v[h:]):
        c = sum(1 for x in part if x["frb"] is not None and x["frb"] <= 78) / len(part); pl = sum(1 for x in part if x["pull"] is not None and x["pull"] <= 150) / len(part)
        bc, bp = base(part[0]["ts"], part[-1]["ts"])
        out.append(f"n {len(part):>3} crowd<=78 {c:.2f} (all {bc:.2f}) pulled<=150 {pl:.2f} (all {bp:.2f})")
    sold_wave = sum(1 for x in v if any(0 <= r <= 40 for r in x["sold_rel"]))
    print(f"  {w[:12]} pools {len(v):>4} sold into the wave (frb..frb+40) in {sold_wave:>3}: first half {out[0]} | second half {out[1]}")
# by the contract they call (a trading-bot router serves many wallets)
print("\nearly outside buyers (first buy at + 1..+ 20, >= 0.0005 ETH) by the contract called: wallets, pools, positions, sold >= 95%, pooled realized return")
byc = collections.defaultdict(list)
for w, v in pos.items():
    for x in v:
        if 1 <= x["first"] <= 20 and x["ein"] >= 0.0005: byc[x["to"]].append((w, x))
for c, v in sorted(byc.items(), key=lambda kv: -len(kv[1]))[:12]:
    cl = [x for w, x in v if x["closed"]]; ein = sum(x["ein"] for x in cl); eout = sum(x["eout"] for x in cl)
    print(f"  {c}: wallets {len({w for w, x in v}):>3} pools {len({x['pool'] for w, x in v}):>4} positions {len(v):>4} sold>=95% {sum(1 for w, x in v if x['frac'] >= 0.95):>4}"
          f" closed {len(cl):>4} in {ein:.4f} out {eout:.4f} pooled {((eout / ein - 1) * 100 if ein else float('nan')):+.1f}%  sold before the crowd {sum(1 for w, x in v if x['last_sell'] is not None and x['frb'] is not None and x['last_sell'] < x['frb'])}")
