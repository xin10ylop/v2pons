"""Sanity checks: (1) price-path validation errors only after the first pull? (2) follow d2/H60 losses below -50% that are not pulls."""
from cands import *
from replay import *
rows = rows_nonvbot(); E = load_ev()
for name in ("C1_eth", "C1_weth", "a98b_hook", "odd2_1444", "564f_weth_hook"):
    rs = [r for r in rows if CANDS[name](r)]
    bad_before_pull = 0; bad = 0; nonpull_big_loss = 0; n = 0
    for r in rs:
        P = prep(r, E[r["pool"]])
        if P["L0"] <= 0: continue
        fp = min(P["pulls"]) if P["pulls"] else 10**12
        s = P["s0"]; first_bad = None
        for w in P["sw"]:
            s2 = buy_step(P["qs"], s, w["L"], w["inp"], w["fee"])[0] if w["buy"] else sell_step(P["qs"], s, w["L"], w["inp"], w["fee"])[0]
            if abs(s2 - w["sqrt"]) / w["sqrt"] > 1e-6 and first_bad is None: first_bad = w["bn"]
            s = w["sqrt"]
        if first_bad is not None:
            bad += 1
            if first_bad < fp: bad_before_pull += 1
        if r.get("frb"):
            a = r["frb"]["off"] + 2; x = replay(r, P, a, a + 60)
            if x: n += 1; nonpull_big_loss += (x["ret"] < -0.5 and not x["pulled"])
    print(f"{name}: pools whose re-simulated price path deviates (>1e-6): {bad}, of which before the first pull: {bad_before_pull}; follow d2/H60 losses < -50% without a pull: {nonpull_big_loss}/{n}")
