"""Robustness for the candidate lines: sell later than frb+1, event exits ("sell into the next real buy after ours"), stake size,
concentration of the PnL. Days as in s08 (d6 = last 24 h)."""
import sys, os, pickle, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
from replay import *
T0 = 1791121962
R = load_rows(); FP = fam_pools(R); E = pickle.load(open(os.path.join(OUT, "ev.pkl"), "rb"))
def day(r): return min(6, int((r["launch_ts"] - T0) // 86400))
def real_buys(r):
    """block offsets of every buy >= 0.005 ETH (any wallet; ours never appear in these families)"""
    o = E[r["pool"]]; qs = r["quote_side"]; out = []
    for e in o["ev"]:
        if e[0] != "s": continue
        if r["dex"] == "v3": dq = e[7] if qs == 0 else e[8]
        else:
            qin, tout = (e[6], e[9]) if qs == 0 else (e[7], e[8]); dq = qin if tout > 0 else 0
        if dq >= 5e15: out.append(e[1] - o["lb"])
    return out
def summarize(label, xs, n_fam, show_days=True):
    if not xs: print(f"  {label}: n 0"); return
    rets = [x["ret"] for x in xs]; usd = [x["usd"] for x in xs]
    share = len(xs) / n_fam
    srt = sorted(usd, reverse=True); top = sum(srt[:max(1, len(srt)//10)]); tot = sum(usd)
    pd = []
    for d in range(7):
        ys = [x["ret"] for x in xs if x["day"] == d]
        pd.append(f"{st.mean(ys)*100:+.1f}%({len(ys)})" if ys else "-")
    print(f"  {label}: n {len(xs)} ({share:.2f}) mean {st.mean(rets)*100:+.1f}% med {st.median(rets)*100:+.1f}% win {sum(1 for v in rets if v > 0)/len(rets):.2f} worst {min(rets)*100:+.0f}% "
          f"pulled {sum(1 for x in xs if x['pulled'])/len(xs):.3f} $/trade {st.mean(usd):+.3f} $/day {st.mean(usd)*n_fam/7*share:+.1f} top10%-share-of-PnL {top/tot if tot > 0 else float('nan'):.2f}" + ("  days " + " ".join(pd) if show_days else ""))
def run(name, rs, rulefn, qeth=0.0058):
    xs = []
    for r in rs:
        ab = rulefn(r)
        if ab is None: continue
        x = replay(r, E[r["pool"]], ab[0], ab[1], qeth)
        if x["ok"]: x["day"] = day(r); xs.append(x)
    return xs
def next_buy_exit(r, a, cap):
    nb = [b for b in real_buys(r) if b >= a]
    return (a, nb[0] + 1) if nb and nb[0] + 1 <= a + cap else (a, a + cap)
SETS = {
    "tok:0f34e3b5": FP["tok:0f34e3b5"],
    "tok:70adce63": FP["tok:70adce63"],
    "tok:d4e7eae4 (V3)": [r for r in FP["tok:d4e7eae4"] if r["dex"] == "v3"],
    "lc:0a493d1a|ac9650d8": FP["lc:0a493d1a|ac9650d8"],
    "lc:0a493d1a|13ead562": FP["lc:0a493d1a|13ead562"],
    "lc:89885b75|d27d1e00": FP["lc:89885b75|d27d1e00"],
    "lc:b09ef517|e9ae5c53": FP["lc:b09ef517|e9ae5c53"],
}
for name, rs in SETS.items():
    n = len(rs)
    print(f"\n### {name} ({n} launches, {n/7:.1f}/day)")
    def af(r): return (r["liq_off"] or 0) + 2
    for k in (1, 2, 3, 5, 10, 20, 40):
        summarize(f"front a=liq+2 b=frb+{k}", run(name, rs, lambda r, k=k: (af(r), r["frb"]["off"] + k) if r["frb"] and r["liq_off"] is not None and r["frb"]["off"] >= af(r) else None), n, show_days=(k in (1, 5, 20)))
    for cap in (100, 300):
        summarize(f"front a=liq+2 sell into next real buy (cap {cap})", run(name, rs, lambda r, cap=cap: next_buy_exit(r, af(r), cap) if r["liq_off"] is not None else None), n)
        summarize(f"follow a=frb+2 sell into next real buy (cap {cap})", run(name, rs, lambda r, cap=cap: next_buy_exit(r, r["frb"]["off"] + 2, cap) if r["frb"] else None), n)
    for qq in (0.02, 0.05, 0.1, 0.2):
        summarize(f"q={qq} ETH front a=liq+2 b=frb+1", run(name, rs, lambda r: (af(r), r["frb"]["off"] + 1) if r["frb"] and r["liq_off"] is not None and r["frb"]["off"] >= af(r) else None, qq), n, show_days=False)
