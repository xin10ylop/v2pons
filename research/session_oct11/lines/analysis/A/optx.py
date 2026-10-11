"""Step 2b: the operator buy transactions (tx cache): calldata heads of the first real buy per candidate line, to find a min-output word."""
from cands import *
from load import load_txs
from replay import prep
rows = rows_nonvbot(); E = load_ev(); T = load_txs()
import pickle
out = {}
for name in ("C1_eth", "C1_weth", "a98b_hook", "564f_weth_hook", "odd2_1444"):
    rs = [r for r in rows if CANDS[name](r) and r.get("frb")]
    fpc = C.Counter(f"{r['frb']['to']}:{r['frb']['sel']}:{r['frb']['clen']}" for r in rs)
    top = fpc.most_common(1)[0][0]
    print(f"\n===== {name}: frb pools {len(rs)}; top frb fingerprint {top} x{fpc[top]}")
    shown = 0; found = 0
    for r in rs:
        if f"{r['frb']['to']}:{r['frb']['sel']}:{r['frb']['clen']}" != top: continue
        P = prep(r, E[r["pool"]]); w = P["sw"][r["frb"]["idx"]] if r["frb"]["idx"] < len(P["sw"]) else None
        if w is None: continue
        x = T.get(w["tx"])
        if not x: continue
        found += 1
        if shown < 4:
            h = x.get("input_head") or x.get("input") or ""
            words = [h[10 + 64 * i: 10 + 64 * (i + 1)] for i in range(6)]
            print("  tx", w["tx"][:12], "value", x["value_wei"] / 1e18, "q", w["q"] / 1e18, "t", w["t"], "nonce", x["nonce"], "from", x["from"][:10])
            for i, wd in enumerate(words): print("     w%d %s  int=%d" % (i, wd, int(wd, 16) if wd else -1))
            shown += 1
    print("  frb txs found in cache:", found)
