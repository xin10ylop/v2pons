"""Q3(a): sniper entries on the curve with the exact curve math. Entry after block create+k; the early surcharge for non-allowlisted buyers
(k22: same second as the create 88-96%, second 1: 6.18%, second 2: 0.19%, second 3+: 0); +1/+2 blocks are in the create's second.
Exit after a fixed hold on the curve; fees 1% + the curve's creator fee each way, gas. Filters on what is visible at entry. By day."""
import pickle, json, collections, sys
from kreplay import *
P = pickle.load(open(os.path.join(DATA, "packed.pkl"), "rb")); CE = P["creates"]; TR = P["trades"]
head = json.load(open(os.path.join(DATA, "trades_head.json")))["head"]
curves = [c for c, cr in CE.items() if 79984897 <= cr["bn"] <= head - 3100]
days = len({day(CE[c]["bn"]) for c in curves}) - 0.0
span_days = (bts(head - 3100) - bts(79984897)) / 86400
print("curves", len(curves), "span days", round(span_days, 2))
CF = {c: cfee(TR.get(c, [])) for c in curves}
res = {}
def feat(c, k):
    cr = CE[c]; ev = TR.get(c, []); lb = cr["bn"]
    Es = {r[4][0] for r in ev if r[3] == "E" and r[2] == cr["tx"]}
    ctx = sum(r[5][0] for r in ev if r[3] == "B" and r[2] == cr["tx"]) / 1e18
    early = [r for r in ev if r[3] in "BS" and r[2] != cr["tx"] and r[0] <= lb + k]
    ob = sum(r[5][0] for r in early if r[3] == "B" and r[4][1] not in Es) / 1e18
    lbuy = sum(r[5][0] for r in early if r[3] == "B" and r[4][1] in Es) / 1e18
    sells = sum(1 for r in early if r[3] == "S")
    return {"ctx": ctx, "other_buy": ob, "listed_buy": lbuy, "sells": sells, "nlisted": len(Es)}
rules = {
    "all": lambda f, cf: True,
    "cf<=1%": lambda f, cf: cf is not None and cf <= 0.01,
    "creator buy >=0.1": lambda f, cf: f["ctx"] >= 0.1,
    "crowd >=0.05 ETH by k, no sell": lambda f, cf: f["other_buy"] >= 0.05 and f["sells"] == 0,
    "crowd >=0.2 ETH by k": lambda f, cf: f["other_buy"] >= 0.2,
    "crowd >=0.2, cf<=1%": lambda f, cf: f["other_buy"] >= 0.2 and cf is not None and cf <= 0.01,
    "allowlist >=3 wallets": lambda f, cf: f["nlisted"] >= 3,
}
out = {}
for k, sur in [(1, 0.93), (2, 0.93), (25, 0.0019), (40, 0.0)]:
    F = {c: feat(c, k) for c in curves}
    for H in ([30, 100, 300, 1000] if k >= 25 else [100]):
        for rn, rf in rules.items():
            if k < 25 and rn != "all": continue
            for stake in (0.002, 0.0058):
                R = []; byd = collections.defaultdict(list); ng = 0
                for c in curves:
                    cf = CF[c]; f = F[c]
                    if not rf(f, cf): continue
                    lb = CE[c]["bn"]
                    x = replay(TR.get(c, []), lb + k, lb + k + H, stake, sur, cf if cf is not None else 0.02)
                    if x is None: continue
                    if x["grad"]: ng += 1; continue
                    R.append(x["ret"]); byd[day(lb)].append(x["ret"])
                s = stats(R, stake, span_days); s["graduated_in_hold_skipped"] = ng
                s["by_day_mean"] = {d: round(sum(v) / len(v), 4) for d, v in sorted(byd.items())}
                key = f"k={k} sur={sur} H={H} rule={rn} stake={stake}"; out[key] = s
                if stake == 0.0058 or k < 25: print(key, {z: s.get(z) for z in ("n", "mean", "median", "win", "worst", "usd_per_day", "graduated_in_hold_skipped")}, s.get("by_day_mean"))
json.dump(out, open(os.path.join(OUT, "k27_sniper.json"), "w"), indent=1)
