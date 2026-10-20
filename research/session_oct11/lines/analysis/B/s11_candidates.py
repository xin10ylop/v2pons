"""Final numbers for the ranked candidates: per (family core, rule) the replay at q = 0.0058 and 0.002 ETH with n, mean, median, win,
worst, pulled-before-sell, the mean without the best 5% of trades, $/day (7-day average and last 24 h), and the per-day means."""
import pickle
from common import *
from replay import Pool
X = pickle.load(open(os.path.join(D, "events.pkl"), "rb")); E, FAM = X["ev"], X["fam"]
rows = {r["pool"]: r for r in load_rows() if r["pool"] in FAM}
def shape_of(r): return (r["quote"], r["fee"], r["tick_spacing"], r["hooks"] == "0x" + "0" * 40)
CAND = [  # name, family substring, core shape, rules [(rule, a-spec, b-spec)]
    ("a98b3b9e hooked core", "#a98b3b9e", ("ETH", 3000, 60, False), ["follow_h60", "follow_h20", "fixfront_h60@44", "front_into"]),
    ("C-1 core", "#cb79985d", ("ETH", 100, 1, True), ["follow_h60", "follow_h20", "fixfront_into@71", "front_into"]),
    ("C-2 core", "6276cbbe#4e451d1a", ("ETH", 500, 1, True), ["follow_h60", "follow_h20"]),
    ("58d59320 via 0xeb7c0347 core", "86b37100", ("WETH", 8388608, 200, False), ["front_into", "follow_h60"]),
    ("operator A 42544ef5", "42544ef5", None, ["follow_h20", "follow_h60", "front_into"]),
    ("operator A 2793923d", "2793923d", None, ["follow_h60", "front_into"]),
    ("hooked one-off f07d1c53", "f07d1c53", None, ["front_into"]),
]
def trades(ps, rule, q):
    out = []
    offs = [rows[p]["frb"]["off"] for p in ps if rows[p]["frb"]]
    p90 = pct(offs, .9)
    for p in ps:
        r = rows[p]; P = Pool(r, E[p]); fo = r["frb"]["off"] if r["frb"] else None; lo = r["liq_off"] or 0; a_eff = max(2, lo + 2)
        if rule.startswith("follow"):
            if fo is None: continue
            a = fo + 2; b = a + int(rule.split("_h")[1])
        elif rule.startswith("fixfront"):
            nm, af = rule.split("@"); a = int(af)
            if fo is not None and fo < a: continue
            b = (fo + 1) if nm == "fixfront_into" and fo is not None else a + 60
        else:   # front_into
            if fo is not None and fo < a_eff: continue
            a = a_eff; b = (fo + 1) if fo is not None else a + max(10, int(p90 + 1 - a))
        x = P.replay(a, b, q)
        if "skip" in x: continue
        out.append((x["ret"], x["pulled"], day(r)))
    return out
res = {}
for name, sub, shape, rules in CAND:
    ps = [p for p, k in FAM.items() if sub in k and "@" not in k and (shape is None or shape_of(rows[p]) == shape)]
    n_l = len(ps); n24 = sum(1 for p in ps if day(rows[p]) == 6)
    for rule in rules:
        for q in (0.0058, 0.002):
            t = trades(ps, rule, q); r = sorted(x[0] for x in t)
            if not r: continue
            k = max(1, int(len(r) * 0.05)); trim = r[:-k]
            stake = q * 2570
            d6 = [x[0] for x in t if x[2] == 6]
            o = {"launches": n_l, "launches_24h": n24, "n": len(r), "mean": sum(r) / len(r), "med": pct(r, .5), "win": sum(1 for v in r if v > 0) / len(r),
                 "worst": r[0], "pulled": sum(1 for x in t if x[1]) / len(t), "mean_trim5": sum(trim) / len(trim),
                 "usd_day": sum(r) / len(r) * stake * len(r) / 7, "n_24h": len(d6), "mean_24h": (sum(d6) / len(d6)) if d6 else None,
                 "usd_24h": sum(d6) * stake if d6 else 0.0,
                 "byday": {DAYS[d]: (sum(1 for x in t if x[2] == d), round(sum(x[0] for x in t if x[2] == d) / max(1, sum(1 for x in t if x[2] == d)), 3)) for d in range(7)}}
            res[f"{name} | {rule} | q={q}"] = o
            print(f"{name:28s} {rule:18s} q={q} launches {n_l} ({n_l/7:.1f}/d, 24h {n24}) n {o['n']} mean {o['mean']:+.3f} med {o['med']:+.3f} win {o['win']:.0%} worst {o['worst']:+.2f} "
                  f"pulled {o['pulled']:.1%} trim5 {o['mean_trim5']:+.3f} $/d {o['usd_day']:+.1f} | 24h n {o['n_24h']} mean {o['mean_24h'] if o['mean_24h'] is None else round(o['mean_24h'],3)} $ {o['usd_24h']:+.1f} | "
                  + " ".join(f"{d}:{c[0]}/{c[1]:+.2f}" for d, c in o["byday"].items() if c[0]))
json.dump(res, open(os.path.join(D, "candidates.json"), "w"), indent=1)
