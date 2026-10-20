"""Engine-style exit (front mode as implemented: buy at L+a; after each block with a buy behind ours, if our position's value is up >= TP,
sell at the head of the next block; else sell at L+a+H). Pull at or before the sell block = -100%. Grid over TP and H, all days and per day."""
from cands import *
from replay import *
rows = rows_nonvbot(); E = load_ev()


def tp_replay(r, P, a, H, tp, q_eth=0.0058):
    lb = P["lb"]; A = lb + a; Bmax = A + H
    s, L, fee = state_before(P, A); qs = P["qs"]
    s, tok = buy_step(qs, s, L, q_units(r, q_eth), fee)
    if tok <= 0: return None
    sell_blk = Bmax; i = 0; sw = [w for w in P["sw"] if A <= w["bn"] < Bmax]
    while i < len(sw):
        blk = sw[i]["bn"]; had_buy = False
        while i < len(sw) and sw[i]["bn"] == blk:
            w = sw[i]; L = w["L"]
            if w["buy"]: s, _ = buy_step(qs, s, L, w["inp"], w["fee"]); had_buy = True
            else: s, _ = sell_step(qs, s, L, w["inp"], w["fee"])
            i += 1
        if had_buy:
            out = to_eth(r, sell_step(qs, s, L, tok, fee)[1])
            if (out - q_eth) / q_eth >= tp:
                sell_blk = blk + 1; break
    b = sell_blk - lb
    return replay(r, P, a, b, q_eth) | {"b": b}


if __name__ == "__main__":
    RES = {}
    for name in ("C1_eth", "C1_weth", "odd2_1444", "564f_weth_hook", "a98b_hook"):
        rs = [r for r in rows if CANDS[name](r)]
        Ps = {r["pool"]: prep(r, E[r["pool"]]) for r in rs}; rs = [r for r in rs if Ps[r["pool"]]["L0"] > 0]
        n = len(rs); print(f"\n===== {name} n={n} ({n/7:.1f}/day)")
        best = None
        for a in (2,):
            for H in (60, 100, 150, 200, 250, 300, 400, 600):
                for tp in (0.01, 0.03, 0.05, 0.10, 0.20):
                    for q in (0.0058, 0.002):
                        res = [tp_replay(r, Ps[r["pool"]], a, H, tp, q) for r in rs]
                        byd = C.defaultdict(list)
                        for r, x in zip(rs, res):
                            if x: byd[day_of(r)].append(x)
                        st = stats(res, n / 7, 1.0); st["by_day"] = {d: stats(byd[d]) for d in range(7)}
                        st["b_p"] = p1050([x["b"] for x in res if x])
                        RES[f"{name}|a{a}|H{H}|tp{tp}|q{q}"] = st
                        if q == 0.0058:
                            dd = " ".join(f"{st['by_day'][d].get('mean', '-'):+.3f}" if st['by_day'][d].get('n') else "-" for d in range(7))
                            print(f"  a{a} H{H:3d} tp{tp:.2f}: n={st['n']} mean={st['mean']:+.4f} med={st['median']:+.4f} win={st['win']:.2f} worst={st['worst']:+.2f} pulled={st['pulled']:.3f} $/tr={st['mean_usd']:+.3f} $/day={st['usd_day']:+.1f} b={st['b_p']} | days {dd}")
    json.dump(RES, open(os.path.join(OUT, "tp_grid.json"), "w"), indent=0, default=str)
