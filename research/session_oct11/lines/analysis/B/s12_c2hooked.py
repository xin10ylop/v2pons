"""Operator C-2's hooked sibling (PoolManager.initialize launches of token template 4e451d1a with a hook): shape, replays, reaction."""
import pickle
from common import *
from replay import Pool
X = pickle.load(open(os.path.join(D, "events.pkl"), "rb")); E, FAM = X["ev"], X["fam"]
rows = {r["pool"]: r for r in load_rows() if r["pool"] in FAM}
ps = [p for p, k in FAM.items() if "6276cbbe#4e451d1a" in k and "@" not in k and rows[p]["hooks"] != "0x" + "0" * 40]
rs = [rows[p] for p in ps]
print("pools", len(ps), "by day", [sum(1 for r in rs if day(r) == d) for d in range(7)], "quote/fee", C.Counter((r["quote"], r["fee"], r["tick_spacing"]) for r in rs).most_common(3),
      "distinct hooks", len({r["hooks"] for r in rs}), "frb", sum(1 for r in rs if r["frb"]), "pulled", sum(1 for r in rs if r["n_pulls"]))
for rule in ("follow_h20", "follow_h60"):
    t = []
    for p in ps:
        r = rows[p]
        if not r["frb"]: continue
        a = r["frb"]["off"] + 2; b = a + int(rule.split("_h")[1])
        x = Pool(r, E[p]).replay(a, b, 0.0058)
        if "skip" not in x: t.append((x["ret"], x["pulled"], day(r)))
    v = sorted(x[0] for x in t)
    print(rule, "n", len(v), f"mean {sum(v)/len(v):+.3f} med {pct(v,.5):+.3f} win {sum(1 for x in v if x>0)/len(v):.0%} pulled {sum(1 for x in t if x[1])/len(t):.0%}",
          "trim5", f"{sum(v[:-max(1,len(v)//20)])/(len(v)-max(1,len(v)//20)):+.3f}", "by day", {DAYS[d]: (sum(1 for x in t if x[2]==d), round(sum(x[0] for x in t if x[2]==d)/max(1,sum(1 for x in t if x[2]==d)),2)) for d in range(7)})
o12 = [r for r in rs if r["outsider12"].get("n")]
print("first-12-swap outsider pools", len(o12), "pulled within 166 blocks of the outsider buy", sum(1 for r in o12 if r["first_pull_off"] is not None and 0 < r["first_pull_off"] - r["outsider12"]["last_off"] <= 166))
# the first real buy, its price move, the wave, the launch shape
from replay import to_eth
fr = [r for r in rs if r["frb"]]
mv = []; wv = {20: [], 60: [], 200: []}
for r in fr:
    P = Pool(r, E[r["pool"]]); i = r["frb"]["idx"]; s = P.sw[i]; sb = P.sw[i - 1][5] if i > 0 else P.sqrt0
    mv.append(100 * ((sb / s[5]) ** 2 - 1))
    for W in wv: wv[W].append(sum(to_eth(x[8], P.quote) for x in P.sw[i + 1:] if x[0] <= s[0] + W and x[2]))
print("frb share", f"{len(fr)/len(rs):.0%}", "off p10/50/90", p3([r["frb"]["off"] for r in fr]), "eth", p3([r["frb"]["eth"] for r in fr]),
      "fp", top([f"{r['frb']['to'][:10]}:{r['frb']['sel']}:{r['frb']['clen']}" for r in fr], 3), "eoas", len({r["frb"]["eoa"] for r in fr}),
      "npools med", med([r["frb"]["eoa_npools_bought"] for r in fr]), "price move % p10/50/90", p3(mv))
print("wave ETH after frb med: +20", round(med(wv[20]), 3), "+60", round(med(wv[60]), 3), "+200", round(med(wv[200]), 3))
print("liq_off p10/50/90", p3([r["liq_off"] for r in rs]), "sqrt0 top share", f"{topshare([r['sqrt_p0'] for r in rs]):.0%}", "clen", top([r["launch"]["calldata_len"] for r in rs], 2))
