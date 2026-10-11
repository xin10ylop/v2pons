"""Slippage tolerance of the router buys (V2 swapExactETHForTokens 7ff36ab5 / b6f9de95: amountOutMin = word 0; V3 SwapRouter02
exactInputSingle 04e45aaf: amountOutMinimum = word 5): amountOutMin / the amount the pool actually paid out. Per family, first real buys
and all fetched router buys."""
import sys, os, pickle
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
R = load_rows(); FP = fam_pools(R); T = pickle.load(open(os.path.join(OUT, "tx.pkl"), "rb")); E = pickle.load(open(os.path.join(OUT, "ev.pkl"), "rb"))
def q(xs, ps=(.1, .25, .5, .75, .9)):
    xs = sorted(xs); return "/".join(f"{xs[min(len(xs)-1, int(p*len(xs)))]:.3f}" for p in ps) if xs else "-"
for name in ["tok:0f34e3b5", "tok:70adce63", "lc:0a493d1a|13ead562", "lc:b09ef517|e9ae5c53", "tok:d4e7eae4", "lc:89885b75|d27d1e00"]:
    ratios_frb, ratios_all, n_tx, sels = [], [], 0, Counter()
    for r in FP[name]:
        o = E[r["pool"]]; qs = r["quote_side"]; lb = o["lb"]
        for e in o["ev"]:
            if e[0] != "s": continue
            t = T.get(e[-1])
            if not t: continue
            if r["dex"] == "v3":
                dq, dt = (e[7], e[8]) if qs == 0 else (e[8], e[7]); buy = dq > 0; out = -dt; eth = dq
            else:
                qin, tin, qout, tout = (e[6], e[7], e[8], e[9]) if qs == 0 else (e[7], e[6], e[9], e[8]); buy = qin > 0 and tout > 0; out = tout; eth = qin
            if not buy: continue
            h = t.get("input_head") or t.get("input") or ""
            sel = t["selector"]; sels[sel] += 1
            mo = None
            if sel in ("7ff36ab5", "b6f9de95") and len(h) >= 10 + 64: mo = int(h[10:74], 16)
            elif sel == "04e45aaf" and len(h) >= 10 + 64 * 6: mo = int(h[10 + 64 * 5: 10 + 64 * 6], 16)
            if mo is None or out <= 0: continue
            rr = mo / out
            ratios_all.append(rr)
            if r["frb"] and e[1] - lb == r["frb"]["off"] and eth / 1e18 >= 0.005: ratios_frb.append(rr)
    print(f"{name}: router-buy selectors {sels.most_common(4)}")
    print(f"   minOut/actual first real buys n={len(ratios_frb)} p10/25/50/75/90 {q(ratios_frb)}  zero-minOut {sum(1 for x in ratios_frb if x == 0)}")
    print(f"   minOut/actual all fetched buys n={len(ratios_all)} {q(ratios_all)}  zero {sum(1 for x in ratios_all if x == 0)}")

# precision for the 0f34e3b5 fleet: (actual - minOut) / actual in parts per million, first real buys and all 7ff36ab5 buys
print("\n0f34e3b5 fleet slack (actual-minOut)/actual in ppm")
for name in ["tok:0f34e3b5", "tok:70adce63"]:
    sl_frb, sl_all = [], []
    for r in FP[name]:
        o = E[r["pool"]]; qs = r["quote_side"]; lb = o["lb"]
        for e in o["ev"]:
            if e[0] != "s": continue
            t = T.get(e[-1])
            if not t or t["selector"] != "7ff36ab5": continue
            qin, tin, qout, tout = (e[6], e[7], e[8], e[9]) if qs == 0 else (e[7], e[6], e[9], e[8])
            if not (qin > 0 and tout > 0): continue
            mo = int(t["input_head"][10:74], 16)
            s = (tout - mo) / tout * 1e6
            sl_all.append(s)
            if r["frb"] and e[1] - lb == r["frb"]["off"]: sl_frb.append(s)
    print(name, "frb n", len(sl_frb), "slack ppm p10/25/50/75/90", q(sl_frb), " exact zero", sum(1 for x in sl_frb if x == 0), "| all n", len(sl_all), q(sl_all), "zero", sum(1 for x in sl_all if x == 0))
