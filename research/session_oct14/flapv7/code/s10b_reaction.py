"""s10: reaction to an outside buyer around our entry. Per launch: did a stranger (not dev, not crowd fingerprint, not a same-tx round trip)
buy in [+60, +100] (our entry is +80)? Then: the first dev drain after it (census pull: dev sell >= 10% of the reserve, or any sell >= 50%),
the dev's first sell of any size after it, and whether the crowd still came. Compared with launches without such a stranger. Also the
census-style quick reaction: a drain <= 30 blocks after the stranger's buy, against the same 30-block window after +80 in launches with
no stranger. -> stdout, data/s10b_reaction.json"""
import json, os, collections as C
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
S = json.load(open(os.path.join(D, "s05_holders.json"))); R = json.load(open(os.path.join(D, "s09_replay.json")))
fam = {r["token"]: r for r in json.load(open(os.path.join(D, "s02_family.json")))["family"]}
TX = {}
for l in open(os.path.join(D, "tx_cache.jsonl")):
    j = json.loads(l); TX[j["h"]] = j
CROWD = set(S["crowd_fp"])
def pct(xs, q):
    xs = sorted(xs)
    if not xs: return None
    k = (len(xs) - 1) * q; f = int(k); c = min(f + 1, len(xs) - 1); return round(xs[f] + (xs[c] - xs[f]) * (k - f), 1)
per = []
for tok, f in fam.items():
    L = f["b"]; dev = {f["from"], f["creator"]}
    trades = []
    for h, t in TX.items():
        for kind, li, tk, who, amt, eth, fee, pp in t["portal"]:
            if tk == tok: trades.append((t["b"] - L, t["ti"], kind, who, t["from"], eth, f"{t['to'][:10]}:{t['sel']}:{t['clen']}:{t['prio']}", h, t))
    trades.sort()
    rt = {h for (_, _, k, _, _, _, _, h, t) in trades if k == "S" and any(x[0] == "B" and x[2] == tok for x in t["portal"])}
    def cls(x):
        off, ti, kind, who, frm, eth, fp, h, t = x
        if h == f["tx"] or frm in dev or who in dev: return "dev"
        if fp in CROWD: return "crowd"
        if h in rt: return "roundtrip"
        return "stranger"
    st = [x for x in trades if x[2] == "B" and cls(x) == "stranger" and 40 <= x[0] <= 120 and x[5] >= 0.0133e18]
    pulls = R["pulls"][tok]
    devsells = [x[0] for x in trades if x[2] == "S" and cls(x) == "dev"]
    crowd = [x[0] for x in trades if x[2] == "B" and cls(x) == "crowd"]
    ref = st[0][0] if st else 80
    o = {"token": tok, "prio": f["prio"], "stranger": bool(st), "ref": ref, "stranger_off": [x[0] for x in st][:5],
         "first_pull_after": next((p[0] - ref for p in pulls if p[0] >= ref), None), "first_pull": pulls[0][0] if pulls else None,
         "pull_before_ref": any(p[0] < ref for p in pulls),
         "dev_sell_after": next((d - ref for d in devsells if d >= ref), None), "crowd_after": sum(1 for c in crowd if c >= ref),
         "crowd_any": len(crowd)}
    per.append(o)
json.dump(per, open(os.path.join(D, "s10b_reaction.json"), "w"))
for nm, sel in (("all", lambda o: True), ("prio 0.07475", lambda o: o["prio"] == 74750000)):
    g = [o for o in per if sel(o) and not o["pull_before_ref"]]
    for s in (True, False):
        h = [o for o in g if o["stranger"] == s]
        fp = [o["first_pull_after"] for o in h if o["first_pull_after"] is not None]
        ds = [o["dev_sell_after"] for o in h if o["dev_sell_after"] is not None]
        q30 = sum(1 for x in fp if x <= 30)
        print(f"{nm:13s} stranger buy in [+40,+120]={s!s:5s}: launches {len(h)}; drain after ref in {len(fp)} (<=30 blocks: {q30}), "
              f"blocks to drain p10/50/90 {[pct(fp, q) for q in (.1,.5,.9)]}; dev's first sell after ref p50 {pct(ds,.5)}; "
              f"crowd buys after ref per launch p50 {pct([o['crowd_after'] for o in h], .5)}, launches with crowd after ref {sum(1 for o in h if o['crowd_after'])}")
