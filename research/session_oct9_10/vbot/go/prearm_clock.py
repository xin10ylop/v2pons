#!/usr/bin/env python3
"""Does the deployer's reaction clock start at an outsider's buy, or at the bot's first buy?
Natural experiment: outsider buys that land BEFORE the bot's first buy (pre-arm), all three PM1444 families.
For each pool with a pre-arm outsider buy: its size, wallet, block; bot buy 1 block; whether the outsider sold (and when);
the pull block. Reports pulled-within-N after bot buy 1 vs baseline, and lag from outsider vs lag from bot buy 1."""
import sys, os, json, collections, statistics as st
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/vbot/react")
from common import *
P, TX, M = load(); BOTW, cls = classifier(TX)
out = []
for v in P.values():
    lim = min(COV[v["src"]], v["pull"] if v["pull"] is not None else 10**9)
    seq = []; ok = True
    for s in v["sw"]:
        if s["rel"] > lim: break
        k, t = cls(v, s)
        if k is None: ok = False; break
        seq.append((s, k, t))
    if not ok: continue
    bb = [s["rel"] for s, k, t in seq if k == "bot" and s["eth"] > 0]
    if not bb: continue
    b1 = bb[0]; b2 = bb[1] if len(bb) > 1 else None
    pre = [(s, t) for s, k, t in seq if k == "out" and s["eth"] > 0 and s["rel"] < b1]
    post = [(s, t) for s, k, t in seq if k == "out" and s["eth"] >= 3e-5 and s["rel"] > b1]
    if not pre:
        out.append({"pid": v["pid"], "fam": v["fam"], "src": v["src"], "b0": v["b0"], "b1": b1, "b2": b2, "pull": v["pull"], "pre": [], "post_first": post[0][0]["rel"] if post else None})
        continue
    pres = []
    for s, t in pre:
        w = t["from"]
        sells = [x["rel"] for x, k, tt in seq if k == "out" and x["eth"] < 0 and tt["from"] == w and x["rel"] >= s["rel"]]
        pres.append({"rel": s["rel"], "eth": s["eth"], "w": w, "sold": sells[0] if sells else None, "to": t["to"]})
    out.append({"pid": v["pid"], "fam": v["fam"], "src": v["src"], "b0": v["b0"], "b1": b1, "b2": b2, "pull": v["pull"], "pre": pres,
                "post_first": post[0][0]["rel"] if post else None})
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "prearm_clock.json"), "w"))
def pr(fam, name, xs):
    if not xs: print(f"  {name}: none"); return
    n = len(xs)
    def pw(x, N):  # pulled within N blocks after bot buy 1 and before any post-arm outsider buy >=3e-5
        return x["pull"] is not None and x["pull"] <= x["b1"] + N and (x["post_first"] is None or x["post_first"] >= x["pull"])
    s = "  ".join(f"<=b1+{N}: {sum(pw(x, N) for x in xs)}" for N in (2, 5, 10, 20, 40))
    print(f"  {name}: pools {n}; pulled before b1 {sum(1 for x in xs if x['pull'] is not None and x['pull'] < x['b1'])}; {s}")
for fam in ("v3.0", "v5.0", "v2.433"):
    F = [x for x in out if x["fam"] == fam]
    print(f"=== {fam}: pools with full tx coverage {len(F)}")
    pr(fam, "no pre-arm outsider buy (baseline)", [x for x in F if not x["pre"]])
    big = lambda x: max((p["eth"] for p in x["pre"]), default=0)
    pr(fam, "pre-arm max buy < 3e-5", [x for x in F if x["pre"] and big(x) < 3e-5])
    pr(fam, "pre-arm max buy >= 3e-5", [x for x in F if x["pre"] and big(x) >= 3e-5])
    pr(fam, "pre-arm max buy >= 1e-4", [x for x in F if x["pre"] and big(x) >= 1e-4])
    W2 = collections.Counter()
    for x in F:
        for p in x["pre"]:
            if p["eth"] >= 3e-5: W2[p["w"][:10]] += 1
    print("  pre-arm >= 3e-5 wallets:", W2.most_common(10))
    # per wallet: pulled within 20 of b1
    byw = collections.defaultdict(list)
    for x in F:
        ws = {p["w"][:10] for p in x["pre"] if p["eth"] >= 3e-5}
        for w in ws: byw[w].append(x)
    for w, xs in sorted(byw.items(), key=lambda kv: -len(kv[1]))[:8]:
        pl = [x for x in xs if x["pull"] is not None and x["pull"] <= x["b1"] + 20 and (x["post_first"] is None or x["post_first"] >= x["pull"])]
        lags_o = [x["pull"] - min(p["rel"] for p in x["pre"] if p["w"][:10] == w) for x in pl]
        lags_b = [x["pull"] - x["b1"] for x in pl]
        sold = [x for x in xs if any(p["w"][:10] == w and p["sold"] is not None for p in x["pre"])]
        sold_b1 = [x for x in xs if any(p["w"][:10] == w and p["sold"] is not None and p["sold"] <= x["b1"] + 3 for p in x["pre"])]
        rels = [p["rel"] for x in xs for p in x["pre"] if p["w"][:10] == w]
        sz = [p["eth"] for x in xs for p in x["pre"] if p["w"][:10] == w]
        print(f"    {w}: pools {len(xs)}, buys at +{min(rels)}..+{max(rels)} (median +{st.median(rels)}), size median {st.median(sz):.1e}; sold at all {len(sold)}, sold by b1+3 {len(sold_b1)};"
              f" pulled <= b1+20 (no later outsider first) {len(pl)}; lag from outsider buy {sorted(lags_o)}; from b1 {sorted(lags_b)}")
