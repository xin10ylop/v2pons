"""p08: exploratory only (many cells, small n: a cell's mean is not a validated rule). Buy at +a, sell at +b on the 48 h launches of each
kind, same replay and conventions as p06 ($15, net of gas, pull = -100%, no trade if pulled at or before +a - 2). Answers one question:
does any simple timing on the value launches look like the 356-B line's lottery? -> p08_timing.out"""
import sys, os, json, statistics as S
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import common as K
X = K.launches(); E = K.events()
L = []
def P(*a): L.append(" ".join(str(v) for v in a)); print(*a)
for kind in ("v0", "val"):
    xs = [x for x in X if (x["len"] == 356) == (kind == "v0")]
    P(f"\n{kind} (n {len(xs)}): mean / median / win % / pulled, $15 net of gas")
    P("  buy\\sell " + " ".join(f"{b:>27d}" for b in (160, 260, 360, 460, 600, 1000)))
    for a in (1, 20, 60, 100, 200):
        cells = []
        for b in (160, 260, 360, 460, 600, 1000):
            if b <= a: cells.append(f"{'-':>27s}"); continue
            rs = [K.trade(x, E[x["pool"]], a, b, 0.0058) for x in xs]; rs = [r for r in rs if r and r.get("ok")]
            rt = [r["ret"] for r in rs]
            cells.append(f"{S.mean(rt)*100:+8.1f} {S.median(rt)*100:+6.2f} {sum(1 for v in rt if v > 0)/len(rt)*100:4.0f} {sum(r['pulled'] for r in rs):3d}")
        P(f"  +{a:<4d}    " + " ".join(cells))
open(K.J("p08_timing.out"), "w").write("\n".join(L) + "\n")
