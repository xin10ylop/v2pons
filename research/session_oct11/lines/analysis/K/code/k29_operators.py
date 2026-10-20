"""Q3(d) repeat operators: creators with many creates (schedule, what follows on their curves, the follow replay per creator), allowlist wallets
reused across curves, and the wallets that trade the most curves: their realised PnL on this venue (ETH out - ETH in + tokens left at the
curve's last price, net of the 1% + creator-fee exit)."""
import pickle, json, collections, statistics as st
from kreplay import *
P = pickle.load(open(os.path.join(DATA, "packed.pkl"), "rb")); CE = P["creates"]; TR = P["trades"]
head = json.load(open(os.path.join(DATA, "trades_head.json")))["head"]
G = {g["curve"] for g in json.load(open(os.path.join(OUT, "k12_grads.json"))) if g.get("curve")}
span_days = (bts(head - 3100) - bts(79984897)) / 86400
curves = [c for c, cr in CE.items() if 79984897 <= cr["bn"] <= head - 3100]
byc = collections.defaultdict(list)
for c in curves: byc[CE[c]["creator"]].append(c)
out = {"n_creators": len(byc), "creators_with_ge10": sum(1 for v in byc.values() if len(v) >= 10), "creates_by_ge10_creators": sum(len(v) for v in byc.values() if len(v) >= 10)}
top = sorted(byc.items(), key=lambda kv: -len(kv[1]))[:15]
rows = []
for cr, cs in top:
    cs = sorted(cs, key=lambda c: CE[c]["bn"])
    gaps = [(bts(CE[b]["bn"]) - bts(CE[a]["bn"])) / 60 for a, b in zip(cs, cs[1:])]
    beth = []; ctx = []; cfs = []; ret = []
    for c in cs:
        ev = TR.get(c, []); lb = CE[c]["bn"]
        beth.append(sum(r[5][0] for r in ev if r[3] == "B" and r[0] <= lb + 3000 and r[2] != CE[c]["tx"]) / 1e18)
        ctx.append(sum(r[5][0] for r in ev if r[3] == "B" and r[2] == CE[c]["tx"]) / 1e18)
        cf = cfee(ev); cfs.append(cf)
        x = replay(ev, lb + 40, lb + 340, 0.0058, 0.0, cf if cf is not None else 0.02)
        if x and not x["grad"]: ret.append(x["ret"])
    hours = collections.Counter(int(time.strftime("%H", time.gmtime(bts(CE[c]["bn"])))) for c in cs)
    days_ = collections.Counter(day(CE[c]["bn"]) for c in cs)
    rows.append({"creator": cr, "n": len(cs), "days": dict(sorted(days_.items())), "gap_min_p10_50_90": [round(sorted(gaps)[int(len(gaps) * q)], 1) for q in (0.1, 0.5, 0.9)] if gaps else None,
                 "create_tx_buy_eth_median": round(st.median(ctx), 4), "others_buy_eth_3000_mean": round(sum(beth) / len(beth), 4), "share_with_other_buys": round(sum(1 for b in beth if b > 0) / len(beth), 3),
                 "creator_fee_top": collections.Counter(round(x * 1e4) if x is not None else None for x in cfs).most_common(2), "graduated": sum(1 for c in cs if c in G),
                 "follow_k40_H300_0.0058": stats(ret, 0.0058, span_days), "hours_top": hours.most_common(3)})
out["top_creators"] = rows
for r in rows: print(r["creator"][:10], r["n"], r["gap_min_p10_50_90"], "ctx", r["create_tx_buy_eth_median"], "others", r["others_buy_eth_3000_mean"], r["share_with_other_buys"], "cf", r["creator_fee_top"], "grad", r["graduated"], "follow", {k: r["follow_k40_H300_0.0058"].get(k) for k in ("n", "mean", "median", "win")})
# allowlisted wallets reused across curves
L = collections.Counter(); Lc = collections.defaultdict(set)
for c in curves:
    for r in TR.get(c, []):
        if r[3] == "E" and r[2] == CE[c]["tx"]: L[r[4][0]] += 1; Lc[r[4][0]].add(CE[c]["creator"])
out["allowlist_wallets"] = len(L); out["allowlist_wallets_in_ge5_curves"] = sum(1 for v in L.values() if v >= 5)
out["allowlist_top"] = [(w, n, len(Lc[w])) for w, n in L.most_common(10)]
print("allowlist wallets", len(L), ">=5 curves", out["allowlist_wallets_in_ge5_curves"], L.most_common(5))
# wallet PnL across the venue (recipient of buys / of sells), window curves, all their events through head
pnl = collections.defaultdict(lambda: {"in": 0, "out": 0, "curves": set(), "early": 0}); last = {}
for c in curves:
    ev = TR.get(c, []); cv = Curve(); hold = collections.Counter(); cf = cfee(ev) or 0.0; lb = CE[c]["bn"]
    for r in ev:
        t = cv.apply(r)
        if not t: continue
        k, eth, tok = t; w = r[4][1]
        if r[4][0] != r[4][1]: w = "router:" + r[4][0]          # router flows: buyer and seller sides cannot be matched by address
        if r[2] == CE[c]["tx"]: w = "creator-tx:" + w
        if k == "B": pnl[w]["in"] += eth; hold[w] += tok
        else: pnl[w]["out"] += r[5][1]; hold[w] -= tok
        pnl[w]["curves"].add(c)
        if k == "B" and r[0] - lb <= 40: pnl[w]["early"] += 1
    if cv.real() < THR:
        for w, tk in hold.items():
            if tk > 0: pnl[w]["out"] += cv.x * tk // (cv.y + tk) * (1 - FEE - cf)     # marked at the curve, exit fees included
    else:
        for w, tk in hold.items():
            if tk > 0: pnl[w]["out"] += 4.2e18 * tk / (204081632653061224489795918 + tk) * (1 - FEE - cf)  # marked at the migration price
W_ = [(w, d) for w, d in pnl.items() if len(d["curves"]) >= 20 and not w.startswith("router:") and not w.startswith("creator-tx:")]
W_.sort(key=lambda x: -len(x[1]["curves"]))
tot_early = [(w, d) for w, d in pnl.items() if d["early"] >= 20 and not w.startswith("router:") and not w.startswith("creator-tx:")]
def agg(L_):
    i = sum(d["in"] for _, d in L_) / 1e18; o = sum(d["out"] for _, d in L_) / 1e18
    return {"wallets": len(L_), "eth_in": round(i, 2), "eth_out_plus_marked": round(o, 2), "pnl_eth": round(o - i, 2), "ret": round(o / i - 1, 4) if i else None,
            "wallets_in_profit": sum(1 for _, d in L_ if d["out"] > d["in"])}
out["wallets_trading_ge20_curves"] = agg(W_)
out["wallets_ge20_early_buys(<=40 blocks)"] = agg(tot_early)
out["creator_tx_buys_all"] = agg([(w, d) for w, d in pnl.items() if w.startswith("creator-tx:")])
out["direct_traders_all"] = agg([(w, d) for w, d in pnl.items() if not w.startswith("creator-tx:") and not w.startswith("router:")])
out["router_flows_excluded"] = agg([(w, d) for w, d in pnl.items() if w.startswith("router:")])
out["top_wallets"] = [{"w": w, "curves": len(d["curves"]), "early_buys": d["early"], "in": round(d["in"] / 1e18, 3), "pnl": round((d["out"] - d["in"]) / 1e18, 3)} for w, d in W_[:15]]
for k in ("wallets_trading_ge20_curves", "wallets_ge20_early_buys(<=40 blocks)", "creator_tx_buys_all", "direct_traders_all", "router_flows_excluded"): print(k, out[k])
for x in out["top_wallets"]: print("  ", x)
json.dump(out, open(os.path.join(OUT, "k29_operators.json"), "w"), indent=1, default=list)
