"""0f34e3b5 fleet: does the fleet quote its minOut from the state of an earlier block or from the latest state? For each first real buy,
the buys before it (same block / earlier blocks) and its slack (actual - minOut)/actual; then the expected slack if the quote had been
taken from the pool state right after the launch (all earlier swaps ignored)."""
import sys, os, pickle
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fams import *
R = load_rows(); FP = fam_pools(R); T = pickle.load(open(os.path.join(OUT, "tx.pkl"), "rb")); E = pickle.load(open(os.path.join(OUT, "ev.pkl"), "rb"))
cases = Counter(); ex = []
for r in FP["tok:0f34e3b5"]:
    if not r["frb"]: continue
    o = E[r["pool"]]; qs = r["quote_side"]; lb = o["lb"]
    X = Y = 0; X0 = Y0 = None; prior = []
    for e in o["ev"]:
        if e[0] == "mi": X += e[6 + qs]; Y += e[7 - qs]; continue
        if e[0] != "s": continue
        if X0 is None: X0, Y0 = X, Y
        qin, tin, qout, tout = (e[6], e[7], e[8], e[9]) if qs == 0 else (e[7], e[6], e[9], e[8])
        if e[1] - lb == r["frb"]["off"] and qin >= 5e15:
            t = T[e[-1]]; mo = int(t["input_head"][10:74], 16)
            slack = (tout - mo) / tout * 1e6
            # quote from the launch state (ignoring every earlier swap)
            out_launch = Y0 * qin * 997 // (X0 * 1000 + qin * 997)
            slack_launch_quote = (tout - out_launch * 0.9995) / tout * 1e6
            same = [p for p in prior if p[0] == e[1]]; earlier = [p for p in prior if p[0] < e[1]]
            k = ("prior same-block" if same else "") + (" prior earlier-block" if earlier else "") or "none before"
            cases[(k, round(slack) == 500, abs(slack - slack_launch_quote) < 1)] += 1
            if earlier and len(ex) < 8: ex.append((r["pool"][:10], e[1] - lb, [(p[0] - lb, p[1] / 1e18) for p in earlier], round(slack, 1), round(slack_launch_quote, 1)))
            break
        if qin > 0: prior.append((e[1], qin))
        X += qin - qout; Y += tin - tout
print("(prior buys, slack==500ppm, slack consistent with a quote from the launch state): count")
for k, v in cases.most_common(): print("  ", k, v)
for x in ex: print("  ex", x)

# quote age: for every fleet buy (7ff36ab5, all fetched, not only the first) with an earlier-block swap before it, was the latest
# earlier swap included in its quote? gap = blocks between that swap and the fleet buy.
print("\nquote freshness of fleet buys vs the gap (blocks) to the previous swap in an earlier block")
from collections import defaultdict
res = defaultdict(lambda: [0, 0])
for r in FP["tok:0f34e3b5"]:
    o = E[r["pool"]]; qs = r["quote_side"]; lb = o["lb"]
    X = Y = 0; hist = []   # (bn, X, Y) state after each event
    for e in o["ev"]:
        if e[0] == "mi": X += e[6 + qs]; Y += e[7 - qs]; hist.append((e[1], X, Y)); continue
        if e[0] == "b": X -= e[6 + qs]; Y -= e[7 - qs]; hist.append((e[1], X, Y)); continue
        qin, tin, qout, tout = (e[6], e[7], e[8], e[9]) if qs == 0 else (e[7], e[6], e[9], e[8])
        t = T.get(e[-1])
        if t and t["selector"] == "7ff36ab5" and qin > 0 and tout > 0:
            mo = int(t["input_head"][10:74], 16)
            earlier = [h for h in hist if h[0] < e[1]]
            if len(earlier) >= 2 and earlier[-1][0] != earlier[-2][0] or len(earlier) >= 2:
                # state at the end of the last earlier block vs the state before it
                lastb = earlier[-1][0]
                prev = [h for h in earlier if h[0] < lastb]
                if prev and len(hist) == len(earlier):   # no same-block swap before this one
                    xs, ys = earlier[-1][1], earlier[-1][2]
                    xp, yp = prev[-1][1], prev[-1][2]
                    q_latest = ys * qin * 997 // (xs * 1000 + qin * 997) * 9995 // 10000
                    q_prev = yp * qin * 997 // (xp * 1000 + qin * 997) * 9995 // 10000
                    gap = e[1] - lastb
                    g = "1" if gap == 1 else "2" if gap == 2 else "3-5" if gap <= 5 else "6-20" if gap <= 20 else ">20"
                    if abs(mo - q_latest) <= max(1, q_latest // 10**6): res[g][0] += 1
                    elif abs(mo - q_prev) <= max(1, q_prev // 10**6): res[g][1] += 1
        X += qin - qout; Y += tin - tout; hist.append((e[1], X, Y))
for g in ("1", "2", "3-5", "6-20", ">20"):
    print(f"  gap {g}: quote includes the last earlier block {res[g][0]}, quote one block stale {res[g][1]}")
