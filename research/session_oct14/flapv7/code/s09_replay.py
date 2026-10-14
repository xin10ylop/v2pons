"""s09: the rule on the recent launches with the census's exact curve (census code/curve.py) driven by the grid's own gsim.Launch.
Rows/events are rebuilt in the grid's format from this study's receipts (Portal TokenBought/TokenSold of each token; every trade touches
the token, so s03's token logs list every trade tx). Pulls as the census: a dev sell (launch wallet / creator, as event seller or tx.from)
removing >= 10% of the curve reserve, or any sell removing >= 50%. Exactness check: every recorded trade replayed from supply 0.
Rule (the BRIEF's): K80 tail, sell at the first buy >= $100 seen in a block (sell in the next block), else +200 after entry; q $5 and $15.
Also K80 hold200 and the per-launch path details. -> data/s09_replay.json, stdout"""
import sys, os, json, collections as C, time
G = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/bnb/grid_flap_sh__Portal_/code"
CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/bnb/census_flap_sh__Portal_/code"
sys.path.insert(0, CEN); sys.path.insert(0, G)
import curve as CV, gsim
import numpy as np
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
Z = "0x" + "0" * 40
fam = {r["token"]: r for r in json.load(open(os.path.join(D, "s02_family.json")))["family"]}
TX = {}
for l in open(os.path.join(D, "tx_cache.jsonl")):
    j = json.loads(l); TX[j["h"]] = j
LOGS = {}
for l in open(os.path.join(D, "toklogs_cache.jsonl")):
    j = json.loads(l); LOGS[j["token"]] = j
HEAD = min(j["to"] for j in LOGS.values())
rows = []; EV = {}; exact = C.Counter()
for tok, f in fam.items():
    L = f["b"]; dev = {f["from"], f["creator"]}
    hs = sorted(set(x[3] for x in LOGS[tok]["logs"]))
    tr = []
    for h in hs:
        t = TX[h]
        for kind, li, tk, who, amt, eth, fee, pp in t["portal"]:
            if tk == tok: tr.append((t["b"] - L, t["ti"], li, kind, amt, eth, fee, who, h, pp))
    tr.sort(key=lambda x: (x[0], x[1], x[2]))
    c = {"r": f["r"], "h": f["h"], "k": f["k"], "version": 7, "dex_thresh": f.get("thresh"), "tax_buy": 0, "tax_sell": 0}
    rr = [[x[3], x[0] + L, x[1], x[2], x[7], x[4], x[5], x[6], x[9], 0, x[8]] for x in tr]
    for kind, obs, mod, ok, capped, ppok in CV.replay(c, rr, 18):
        exact[(kind, ok or capped, ppok)] += 1
    # pulls (census definition)
    s = 0; pulls = []; peak = 0
    def resv(s_): return CV.est_reserve(f["r"], f["h"], f["k"], s_)
    for x in tr:
        off, ti, li, kind, amt, eth, fee, who, h, pp = x
        if kind == "B": s += amt
        else:
            r0 = resv(s); r1 = resv(s - amt); frac = (r0 - r1) / r0 if r0 > 0 else 0
            t = TX[h]; isdev = who in dev or t["from"] in dev
            if (isdev and frac >= 0.10) or frac >= 0.5:
                pulls.append((off, "dev" if isdev and frac >= 0.10 else "dump", frac, t["from"], False, (r0 - r1) / 1e18))
            s -= amt
    row = {"token": tok, "r": f["r"], "h": f["h"], "k": f["k"], "quote_dec": 18, "tax_buy_bps": 0, "tax_sell_bps": 0, "version": 7,
           "dex_thresh": f.get("thresh"), "quote_bnb_per_unit": 1.0, "quote": Z, "launch_tx": f["tx"], "pulls": pulls, "grad": None, "graduated": False,
           "launch_ts": f["ts"], "launch_block": L, "prio": f["prio"]}
    rows.append(row); EV[tok] = {"t": tr}
print("exactness (kind, amount exact|capped, postPrice exact):", dict(exact))
# rule indices
RI_X = gsim.RULES.index(("X", 100, 200)); RI_H = gsim.RULES.index(("H", None, 200)); KI = gsim.KS.index(80)
res = {}
for q in (5, 15):
    for place in ("tail", "head"):
        out = []
        for r in rows:
            Lh = gsim.Launch(r, EV[r["token"]])
            if r["launch_block"] + 80 + 201 > HEAD: out.append({"token": r["token"], "skip": "too recent"}); continue
            sk, raw, S, hit, ng = Lh.grid(q, place == "tail")
            o = {"token": r["token"], "ts": r["launch_ts"], "prio": r["prio"], "skip": int(sk[KI])}
            if not sk[KI]:
                o.update({"X": float(raw[KI, RI_X]), "X_s": int(S[KI, RI_X]), "X_hit": bool(hit[KI, RI_X]), "H200": float(raw[KI, RI_H]), "H200_hit": bool(hit[KI, RI_H])})
            o["first_pull"] = r["pulls"][0][:3] if r["pulls"] else None
            out.append(o)
        res[f"q{q}_{place}"] = out
def summ(xs):
    xs = [x for x in xs if x is not None]
    if not xs: return "n 0"
    a = np.array(xs); return f"n {len(a)} mean {a.mean()*100:+.1f}% median {np.median(a)*100:+.1f}% win {(a>0).mean()*100:.0f}% worst {a.min()*100:+.1f}% best {a.max()*100:+.1f}%"
for k, out in res.items():
    tr_ = [o for o in out if o.get("skip") == 0 and "X" in o]
    print(f"\n{k}: launches {len(out)}, traded {len(tr_)}, skipped {C.Counter(o['skip'] for o in out if o.get('skip'))}")
    print("  rule K80 next-buy>=$100 dl200:", summ([o["X"] for o in tr_]), "| drain hit", sum(o["X_hit"] for o in tr_), "| trigger exits", sum(1 for o in tr_ if o["X_s"] < 200))
    print("  K80 hold200                  :", summ([o["H200"] for o in tr_]))
    for nm, sel in (("prio 0.07475", lambda o: o["prio"] == 74750000), ("prio 0.0715", lambda o: o["prio"] == 71500000), ("other prio", lambda o: o["prio"] not in (74750000, 71500000))):
        print(f"    {nm:13s}", summ([o["X"] for o in tr_ if sel(o)]))
    days = C.defaultdict(list)
    for o in tr_: days[time.strftime("%m-%d", time.gmtime(o["ts"]))].append(o["X"])
    print("    by day:", {d: summ(v) for d, v in sorted(days.items())})
json.dump({"head": HEAD, "exact": {str(k): v for k, v in exact.items()}, "res": res, "pulls": {r["token"]: r["pulls"] for r in rows}},
          open(os.path.join(D, "s09_replay.json"), "w"))
