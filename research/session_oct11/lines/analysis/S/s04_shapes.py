"""S04: the line's launches per window (last 6 / 24 / 48 h before the s01 head), the line shape check (fee 100, one mint by the launch wallet
of a one-sided range (-887272, 204200) or its mirror), the launcher's own first buy (size, offset from the launch and from the mint,
minOut, route), the mint offset, the later own buys, outsiders' buys before the own buy, and pulls. -> s04_shapes.out"""
import sys, os, time, statistics as st
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scommon import *
D, R = load(); S1 = json.load(open(os.path.join(OUT, "s01_launches.json"))); TH = S1["t_head"]
out = []
def P(s=""): out.append(s)
def line_shape(r):
    m = r["mints"]
    return r["fee"] == 100 and len(m) >= 1 and m[0]["by_lw"] and (m[0]["lo"], m[0]["hi"]) in ((-887272, 204200), (-204200, 887272))
def q(xs, f="%g"):
    xs = sorted(xs)
    if not xs: return "-"
    return f"n {len(xs)} min {f % xs[0]} p10 {f % xs[int(.1 * (len(xs) - 1))]} med {f % xs[len(xs) // 2]} p90 {f % xs[int(.9 * (len(xs) - 1))]} max {f % xs[-1]}"
if __name__ == "__main__":
    P(f"s01 head {S1['head']} at {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(TH))} UTC; s02 head {D['head']}; 13ead562 pool creations in 50 h: {len(S1['launches'])} "
      f"(WETH side {len(R)}); NonfungiblePositionManager code hash {S1['npm_code_hash'][:8]}")
    odd = [r for r in R if not line_shape(r)]
    P(f"not the line's shape ({len(odd)}): " + "; ".join(f"{r['lb']} fee {r['fee']} wallet {r['lw'][:10]} mint {[(m['off'], '%.4g' % m['L'], m['lo'], m['hi']) for m in r['mints']]}" for r in odd))
    LR = [r for r in R if line_shape(r)]
    P(f"line launches (shape ok): {len(LR)}; L tiers {Counter('%.4g' % r['mints'][0]['L'] for r in LR).most_common()}")
    for hrs in (6, 12, 24, 48):
        xs = [r for r in LR if TH - r["ts"] <= hrs * 3600]
        P(f"\n=== last {hrs} h: {len(xs)} launches ({len(xs) * 24 / hrs:.1f}/day), wallets {len(set(r['lw'] for r in xs))}")
        if not xs: continue
        P(f"  own first buy size: {Counter(round(r['own1']['eth'], 4) if r['own1'] else None for r in xs).most_common()}")
        P(f"  own first buy route: {Counter((r['own1']['to'][:10], r['own1']['sel'], r['own1']['len'], r['own1']['min_out']) if r['own1'] else None for r in xs).most_common()}")
        P(f"  mint offset: {q([r['mints'][0]['off'] for r in xs], '%d')}")
        for lab, f in (("0.05", lambda r: r["own1"] and abs(r["own1"]["eth"] - 0.05) < 1e-9), ("other size", lambda r: r["own1"] and abs(r["own1"]["eth"] - 0.05) >= 1e-9)):
            ys = [r for r in xs if f(r)]
            P(f"  own first buy {lab}: offset from launch {q([r['own1']['off'] for r in ys], '%d')}; from the mint {q([r['own1']['off'] - r['mints'][0]['off'] for r in ys], '%d')}")
        P(f"  own buys per pool to +5000: {Counter(len(r['own']) for r in xs).most_common()}; own sells to +5000: {sum(1 for r in xs for s in r['swaps'] if s['by_lw'] and s['dir'] == 'S')}")
        pre = [r for r in xs if r["own1"] and any(s["dir"] == "B" and not s["by_lw"] and s["off"] <= r["own1"]["off"] for s in r["swaps"])]
        P(f"  outsider buy at or before the own first buy: {len(pre)}; no own buy at all: {sum(1 for r in xs if not r['own1'])}")
        pl = [r for r in xs if r["pull1"]]
        P(f"  pulled by +5000: {len(pl)}/{len(xs)}; pull offset {q([r['pull1']['off'] for r in pl], '%d')}; by the launch wallet {sum(1 for r in pl if r['pull1']['by_lw'])}; "
          f"pull - own first buy {q([r['pull1']['off'] - r['own1']['off'] for r in pl if r['own1']], '%d')}")
    P("\n=== every line launch of the last 24 h (and the 6 h before it), newest last")
    for r in LR:
        if TH - r["ts"] > 30 * 3600: continue
        o = r["own1"]; m = r["mints"][0]
        oth = [s for s in r["swaps"] if not s["by_lw"] and s["off"] <= 400]
        P(f"  {r['lb']} {time.strftime('%m-%d %H:%M', time.gmtime(r['ts']))} ({(TH - r['ts']) / 3600:.1f} h) {r['lw'][:10]} n{r['nonce']} mint +{m['off']} L {m['L']:.4g} "
          f"own1 {('+%d %.4f ETH minOut %s' % (o['off'], o['eth'], o['min_out'])) if o else 'none'} (own -mint {o['off'] - m['off'] if o else '-'}) "
          f"later own {[('+%d' % s['off'], s['eth']) for s in r['own'][1:]]} others<=400 {[('+%d' % s['off'], s['dir'], round(s['eth'], 4), s['from'][:8], s.get('sel')) for s in oth]} "
          f"pull {('+%d' % r['pull1']['off']) if r['pull1'] else 'none to +%d' % (r['ev_to'] - r['lb'])}")
    open(os.path.join(OUT, "s04_shapes.out"), "w").write("\n".join(out) + "\n"); print("\n".join(out))
