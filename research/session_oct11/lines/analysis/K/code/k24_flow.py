"""Q2: the trade flow on every ETH curve created in the window (and on the 200 most recent with a complete 3,000-block window):
buys/sells/ETH/wallets in the first 3,000 blocks, the creator's and the allowlist's buys, snipers, graduation and the price path."""
import json, pickle, collections, statistics as st
from kload import *
from kcurve import *
P = pickle.load(open(os.path.join(DATA, "packed.pkl"), "rb")); CE = P["creates"]; TR = P["trades"]
head = json.load(open(os.path.join(DATA, "trades_head.json")))["head"]
G = {g["curve"]: g for g in json.load(open(os.path.join(OUT, "k12_grads.json"))) if g.get("curve")}
G2 = {g["token"]: g for g in json.load(open(os.path.join(OUT, "k12_grads.json")))}
OFFS = [1, 2, 5, 10, 30, 100, 300, 1000, 3000]
rows = []
for c, cr in CE.items():
    if cr["bn"] < 79984897 or cr["bn"] > head - 3000: continue
    ev = TR.get(c, []); cv = Curve(); lb = cr["bn"]
    Es = {r[4][0] for r in ev if r[3] == "E" and r[2] == cr["tx"]}
    xs = {r[2] for r in ev if r[3] == "X"}
    o = {"curve": c, "bn": lb, "day": day(lb), "creator": cr["creator"], "n_listed": len(Es), "nb": 0, "ns": 0, "beth": 0, "seth": 0, "wallets": set(),
         "creator_tx_buy": 0, "creator_buys_after": 0, "creator_sells": 0, "listed_buy_eth": 0, "listed_sell_eth": 0, "snipe_n": 0, "snipe_eth": 0,
         "path": {}, "max_px": 1.0, "real_3000": 0, "grad_bn": None, "first_sell_dt": None}
    p0 = cv.price(); i = 0
    for off in OFFS:
        while i < len(ev) and ev[i][0] <= lb + off:
            r = ev[i]; i += 1
            t = cv.apply(r)
            if not t: continue
            k, eth, tok = t; buyer = r[4][1]
            if k == "B":
                o["nb"] += 1; o["beth"] += eth; o["wallets"].add(buyer)
                if r[2] == cr["tx"]: o["creator_tx_buy"] += eth
                elif buyer == cr["creator"]: o["creator_buys_after"] += eth
                if buyer in Es: o["listed_buy_eth"] += eth
                if r[2] in xs: o["snipe_n"] += 1; o["snipe_eth"] += eth
            else:
                o["ns"] += 1; o["seth"] += eth; o["wallets"].add(r[4][0])
                if o["first_sell_dt"] is None: o["first_sell_dt"] = r[0] - lb
                if r[4][0] == cr["creator"]: o["creator_sells"] += eth
                if r[4][0] in Es: o["listed_sell_eth"] += eth
            o["max_px"] = max(o["max_px"], cv.price() / p0)
        o["path"][off] = cv.price() / p0
    o["real_3000"] = cv.real() / 1e18
    g = G.get(c) or G2.get(cr["token"])
    if g: o["grad_bn"] = g["full_bn"] - lb
    o["n_wallets"] = len(o.pop("wallets"))
    rows.append(o)
pickle.dump(rows, open(os.path.join(DATA, "k24_rows.pkl"), "wb"))
def summ(R, label):
    n = len(R); E = lambda f: [f(r) for r in R]
    q = lambda v: [round(sorted(v)[int(len(v) * z)], 4) for z in (0.1, 0.5, 0.9)] if v else None
    out = {"label": label, "n": n,
           "with_any_trade_after_create_tx": sum(1 for r in R if r["nb"] + r["ns"] > (1 if r["creator_tx_buy"] else 0)),
           "buys_p10_50_90": q(E(lambda r: r["nb"])), "sells_p10_50_90": q(E(lambda r: r["ns"])), "mean_buys": round(sum(E(lambda r: r["nb"])) / n, 2),
           "buy_eth_p10_50_90": q(E(lambda r: r["beth"] / 1e18)), "mean_buy_eth": round(sum(E(lambda r: r["beth"])) / n / 1e18, 4), "mean_sell_eth": round(sum(E(lambda r: r["seth"])) / n / 1e18, 4),
           "wallets_p10_50_90": q(E(lambda r: r["n_wallets"])),
           "creator_buy_in_create_tx_share": round(sum(1 for r in R if r["creator_tx_buy"]) / n, 3), "creator_buy_in_create_tx_eth_median_when_any": st.median([r["creator_tx_buy"] / 1e18 for r in R if r["creator_tx_buy"]] or [0]),
           "creator_buys_after_share": round(sum(1 for r in R if r["creator_buys_after"]) / n, 3), "creator_sold_share": round(sum(1 for r in R if r["creator_sells"]) / n, 3),
           "allowlist_share": round(sum(1 for r in R if r["n_listed"] > 1) / n, 3), "listed_buy_eth_mean": round(sum(E(lambda r: r["listed_buy_eth"])) / n / 1e18, 4), "listed_sell_eth_mean": round(sum(E(lambda r: r["listed_sell_eth"])) / n / 1e18, 4),
           "sniped_share": round(sum(1 for r in R if r["snipe_n"]) / n, 3), "snipe_eth_mean": round(sum(E(lambda r: r["snipe_eth"])) / n / 1e18, 4),
           "real_eth_at_3000_p10_50_90": q(E(lambda r: r["real_3000"])), "graduated_within_3000": sum(1 for r in R if r["grad_bn"] is not None and r["grad_bn"] <= 3000),
           "graduated_ever": sum(1 for r in R if r["grad_bn"] is not None),
           "price_path_median": {o: round(st.median(E(lambda r: r["path"][o])), 4) for o in OFFS}, "price_path_mean": {o: round(sum(E(lambda r: r["path"][o])) / n, 4) for o in OFFS},
           "max_px_p50_90": q(E(lambda r: r["max_px"]))}
    return out
res = {"all": summ(rows, "all ETH curves (complete 3,000-block window)"), "recent200": summ(sorted(rows, key=lambda r: -r["bn"])[:200], "200 most recent")}
res["by_day"] = {d: {"n": len(v), "graduated_ever": sum(1 for r in v if r["grad_bn"] is not None), "mean_buy_eth": round(sum(r["beth"] for r in v) / len(v) / 1e18, 4),
                     "with_buy_after_create": sum(1 for r in v if r["nb"] > (1 if r["creator_tx_buy"] else 0))} for d, v in sorted(collections.defaultdict(list, {}).items())}
byd = collections.defaultdict(list)
for r in rows: byd[r["day"]].append(r)
res["by_day"] = {d: {"n": len(v), "graduated_ever": sum(1 for r in v if r["grad_bn"] is not None), "grad_within_3000": sum(1 for r in v if r["grad_bn"] is not None and r["grad_bn"] <= 3000),
                     "mean_buy_eth_3000": round(sum(r["beth"] for r in v) / len(v) / 1e18, 4), "sum_buy_eth_3000": round(sum(r["beth"] for r in v) / 1e18, 2),
                     "sniped": sum(1 for r in v if r["snipe_n"])} for d, v in sorted(byd.items())}
gb = sorted(r["grad_bn"] for r in rows if r["grad_bn"] is not None)
res["grad_blocks_after_create_p10_25_50_75_90"] = [gb[int(len(gb) * z)] for z in (0.1, 0.25, 0.5, 0.75, 0.9)] if gb else None
json.dump(res, open(os.path.join(OUT, "k24_flow.json"), "w"), indent=1)
print(json.dumps(res, indent=1))
