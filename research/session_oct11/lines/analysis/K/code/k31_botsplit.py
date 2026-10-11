"""split the top direct traders' PnL into curves that graduated vs not, and realised vs marked."""
import pickle, json, collections, sys
from kreplay import *
P = pickle.load(open(os.path.join(DATA, "packed.pkl"), "rb")); CE = P["creates"]; TR = P["trades"]
head = json.load(open(os.path.join(DATA, "trades_head.json")))["head"]
out = {}
for w in sys.argv[1:]:
    acc = collections.defaultdict(lambda: {"n": 0, "in": 0, "out_real": 0, "mark": 0})
    for c, ev in TR.items():
        cr = CE[c]
        if not 79984897 <= cr["bn"] <= head - 3100: continue
        if not any(w in r[4] for r in ev if r[3] in "BS"): continue
        cv = Curve(); ein = eout = tok = 0
        for r in ev:
            t = cv.apply(r)
            if not t or w not in r[4]: continue
            if t[0] == "B": ein += t[1]; tok += t[2]
            else: eout += r[5][1]; tok -= t[2]
        if ein == 0: continue
        cf = cfee(ev) or 0; g = cv.real() >= THR
        mark = 0 if tok <= 0 else (cv.x * tok // (cv.y + tok) * (1 - FEE - cf) if not g else 4.2e18 * tok / (204081632653061224489795918 + tok) * (1 - FEE - cf))
        a = acc["graduated" if g else "not graduated"]; a["n"] += 1; a["in"] += ein / 1e18; a["out_real"] += eout / 1e18; a["mark"] += mark / 1e18
    out[w] = {k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in acc.items()}
    print(w, out[w])
json.dump(out, open(os.path.join(OUT, "k31_botsplit.json"), "w"), indent=1)
