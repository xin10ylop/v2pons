"""profile the venue's largest direct traders that buy early: per curve their first-buy offset, the curve's real ETH at entry, ETH in/out,
hold, and their realised return; is there a rule we could copy?"""
import pickle, json, collections, statistics as st, sys
from kreplay import *
P = pickle.load(open(os.path.join(DATA, "packed.pkl"), "rb")); CE = P["creates"]; TR = P["trades"]
head = json.load(open(os.path.join(DATA, "trades_head.json")))["head"]
W = sys.argv[1:] or ["0x9689992f5b5c09447f15906d8d11214944488341", "0xe492912f37c2a4eca45d42dc67548f4c6cd7ce2b", "0xf0b7eaaf868191adc00065ca13391ef436ce8faf"]
res = {}
for w in W:
    rows = []
    for c, ev in TR.items():
        cr = CE[c]
        if not 79984897 <= cr["bn"] <= head - 3100: continue
        mine = [r for r in ev if r[3] in "BS" and w in r[4]]
        if not mine: continue
        cv = Curve(); i = 0; ein = eout = 0; tok = 0; first = None; lastS = None; real_at = None; via = collections.Counter()
        for r in ev:
            pre_real = cv.real()
            t = cv.apply(r)
            if not t or w not in r[4]: continue
            k, eth, tk = t; via[(r[4][0] == r[4][1])] += 1
            if k == "B":
                if first is None: first = r[0] - cr["bn"]; real_at = pre_real / 1e18
                ein += eth; tok += tk
            else: eout += r[5][1]; tok -= tk; lastS = r[0] - cr["bn"]
        cf = cfee(ev) or 0
        if tok <= 0: mark = 0
        elif cv.real() < THR: mark = cv.x * tok // (cv.y + tok) * (1 - FEE - cf)
        else: mark = 4.2e18 * tok / (204081632653061224489795918 + tok) * (1 - FEE - cf)     # graduated: marked at the migration pool's first price
        if ein == 0: continue
        rows.append({"dt": first, "real_at": real_at, "in": ein / 1e18, "out": (eout + mark) / 1e18, "hold": (lastS - first) if lastS is not None else None, "cf": cf, "direct_share": via[True] / sum(via.values()), "day": day(cr["bn"])})
    if not rows: continue
    r_ = [x["out"] / x["in"] - 1 for x in rows]
    def q(v): v = sorted(v); return [round(v[int(len(v) * z)], 4) for z in (0.1, 0.25, 0.5, 0.75, 0.9)]
    d = {"curves": len(rows), "eth_in": round(sum(x["in"] for x in rows), 2), "pnl": round(sum(x["out"] - x["in"] for x in rows), 2), "per_curve_ret_q": q(r_), "win": round(sum(1 for x in r_ if x > 0) / len(r_), 3),
         "entry_dt_q": q([x["dt"] for x in rows]), "real_at_entry_q": q([x["real_at"] for x in rows]), "in_q": q([x["in"] for x in rows]), "hold_q": q([x["hold"] for x in rows if x["hold"] is not None]),
         "cf_top": collections.Counter(round(x["cf"] * 1e4) for x in rows).most_common(4), "direct_share": round(st.mean(x["direct_share"] for x in rows), 3),
         "by_day_pnl": {dd: round(sum(x["out"] - x["in"] for x in rows if x["day"] == dd), 2) for dd in sorted({x["day"] for x in rows})}}
    by = collections.defaultdict(list)
    for x in rows: by["dt<=40" if x["dt"] <= 40 else "dt41-300" if x["dt"] <= 300 else "dt>300"].append(x)
    d["by_entry"] = {k: {"n": len(v), "in": round(sum(x["in"] for x in v), 2), "pnl": round(sum(x["out"] - x["in"] for x in v), 2)} for k, v in by.items()}
    res[w] = d; print(w, json.dumps(d))
json.dump(res, open(os.path.join(OUT, "k30_botprofile.json"), "w"), indent=1)
