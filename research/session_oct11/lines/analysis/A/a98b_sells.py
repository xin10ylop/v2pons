"""a98b (hooked, 2020-byte) and 564f (hooked WETH) lines: do sells happen at all (honeypot check), who sells, and the buy flow."""
from cands import *
from replay import prep
from load import load_txs
rows = rows_nonvbot(); E = load_ev(); T = load_txs()
for name in ("a98b_hook", "564f_weth_hook", "C1_eth"):
    rs = [r for r in rows if CANDS[name](r)]
    hk = [r for r in rs if r["hooks"] != Z40]; nh = [r for r in rs if r["hooks"] == Z40]
    for lab, grp in (("hooked", hk), ("no hook", nh)):
        if not grp: continue
        nb = [r["n_buys"] for r in grp]; ns = [r["n_sells"] for r in grp]
        sell_eoas = C.Counter(); sell_fp = C.Counter(); sell_by_lw = 0; nsell_known = 0; sell_first_off = []
        for r in grp:
            P = prep(r, E[r["pool"]])
            ss = [w for w in P["sw"] if not w["buy"]]
            if ss: sell_first_off.append(ss[0]["bn"] - P["lb"])
            for w in ss:
                x = T.get(w["tx"])
                if not x: continue
                nsell_known += 1; sell_eoas[x["from"]] += 1; sell_fp[f"{(x['to'] or '')[:10]}:{x['selector']}"] += 1
                if x["from"] == r["launch"]["from"]: sell_by_lw += 1
        print(f"{name} [{lab}] pools {len(grp)}: buys/pool p10/50/90 {p1050(nb)}, sells/pool {p1050(ns)}, pools with any sell {sum(1 for x in ns if x)}; first sell off {p1050(sell_first_off)}; "
              f"sells with tx known {nsell_known}: distinct EOAs {len(sell_eoas)}, top {[(k[:10], v) for k, v in sell_eoas.most_common(3)]}, fp {sell_fp.most_common(3)}, by launch wallet {sell_by_lw}")
