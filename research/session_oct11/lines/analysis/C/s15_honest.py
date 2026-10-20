"""Honest per-launch rules: we buy every launch of the line at a = liq_off + 2 (the block after the liquidity add + 2), sell k blocks after
the first real buy (>= 0.005 ETH) that lands at or after our buy, or at the cap C if none comes before C - k. Every launch is traded
(tradable share = 1). For tok:0f34e3b5 the fleet's buys that would revert because of our buy (swapExactETHForTokens with 0.05% slack and
a quote 1-2 blocks stale, see s10) are removed: blocks [a, a+2] (and the variant [a, a+5]). d6 = last 24 h. Q_ETH env = stake."""
import sys, os, pickle, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
from replay import *
T0 = 1791121962; Q = float(os.environ.get("Q_ETH", "0.0058"))
R = load_rows(); FP = fam_pools(R); E = pickle.load(open(os.path.join(OUT, "ev.pkl"), "rb")); T = pickle.load(open(os.path.join(OUT, "tx.pkl"), "rb"))
def day(r): return min(6, int((r["launch_ts"] - T0) // 86400))
def buys(r):
    o = E[r["pool"]]; qs = r["quote_side"]; out = []
    for e in o["ev"]:
        if e[0] != "s": continue
        if r["dex"] == "v3": dq = e[7] if qs == 0 else e[8]
        else:
            qin, tout = (e[6], e[9]) if qs == 0 else (e[7], e[8]); dq = qin if tout > 0 else 0
        if dq > 0: out.append((e[1] - o["lb"], dq, e))
    return out
def plan(r, k, C, drop_win=None):
    a = (r["liq_off"] or 0) + 2
    drop = set()
    if drop_win is not None:
        for off, dq, e in buys(r):
            t = T.get(e[-1])
            if a <= off <= a + drop_win and t and t["selector"] == "7ff36ab5": drop.add((e[1], e[3]))
    trig = [off for off, dq, e in buys(r) if off >= a and dq >= 5e15 and (e[1], e[3]) not in drop]
    b = trig[0] + k if trig and trig[0] + k <= C else C
    return a, b, drop
def summarize(label, xs, n_fam):
    rets = [x["ret"] for x in xs]; usd = [x["usd"] for x in xs]
    pd = []
    for d in range(7):
        ys = [x["ret"] for x in xs if x["day"] == d]
        pd.append(f"{st.mean(ys)*100:+.1f}%({len(ys)})" if ys else "-")
    return (f"  {label}: n {len(xs)}/{n_fam} mean {st.mean(rets)*100:+.1f}% med {st.median(rets)*100:+.1f}% win {sum(1 for v in rets if v > 0)/len(rets):.2f} "
            f"worst {min(rets)*100:+.0f}% pulled<=sell {sum(1 for x in xs if x['pulled'])/len(xs):.3f} $/trade {st.mean(usd):+.3f} $/day {st.mean(usd)*len(xs)/7:+.1f}  days d0..d6 " + " ".join(pd))
SETS = {
    "tok:0f34e3b5": (FP["tok:0f34e3b5"], [(1, 300, None), (1, 300, 2), (1, 300, 5), (1, 150, 2), (20, 300, 2)]),
    "tok:70adce63": (FP["tok:70adce63"], [(1, 300, None), (1, 600, None), (5, 300, None)]),
    "tok:d4e7eae4 (V3 part)": ([r for r in FP["tok:d4e7eae4"] if r["dex"] == "v3"], [(1, 150, None), (1, 300, None), (5, 300, None), (20, 300, None), (1, 600, None)]),
    "lc:0a493d1a|ac9650d8": (FP["lc:0a493d1a|ac9650d8"], [(1, 300, None), (5, 300, None), (20, 300, None)]),
    "lc:0a493d1a|13ead562": (FP["lc:0a493d1a|13ead562"], [(1, 60, None), (1, 100, None), (5, 60, None)]),
    "lc:89885b75|d27d1e00 value-0 launches": ([r for r in FP["lc:89885b75|d27d1e00"] if r["launch"]["value_eth"] == 0], [(1, 300, None), (1, 600, None), (20, 600, None)]),
    "lc:89885b75|d27d1e00 all": (FP["lc:89885b75|d27d1e00"], [(1, 600, None)]),
    "lc:b09ef517|e9ae5c53": (FP["lc:b09ef517|e9ae5c53"], [(1, 1000, None), (1, 2000, None)]),
}
if __name__ == "__main__":
    lines = [f"q = {Q} ETH"]
    for name, (rs, variants) in SETS.items():
        lines.append(f"\n### {name}: {len(rs)} launches ({len(rs)/7:.1f}/day)")
        for k, C, dw in variants:
            xs = []
            for r in rs:
                if r["liq_off"] is None: continue
                a, b, drop = plan(r, k, C, dw)
                x = replay(r, E[r["pool"]], a, b, Q, drop)
                if x["ok"]: x["day"] = day(r); xs.append(x)
            lab = f"front a=liq+2, sell first real buy+{k} (cap {C})" + (f", fleet buys in [a,a+{dw}] revert" if dw is not None else "")
            lines.append(summarize(lab, xs, len(rs)))
    out = "\n".join(lines)
    open(os.path.join(OUT, f"s15_honest{'_q'+str(Q) if Q != 0.0058 else ''}.out"), "w").write(out + "\n"); print(out)
