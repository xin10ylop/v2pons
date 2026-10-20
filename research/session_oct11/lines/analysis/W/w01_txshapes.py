"""V3 crowd line: the shapes of the transactions behind its swaps (from analyst C's tx.pkl): to/selector/len/value for real buys (>= 0.005 ETH),
for small buys, and for sells; one full input per shape (crowd bot contracts, SwapRouter02 0xcaf681a6 buy and sell)."""
import pickle
from collections import Counter, defaultdict
C = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/analysis/C"
R = pickle.load(open(C + "/v23.pkl", "rb")); E = pickle.load(open(C + "/ev.pkl", "rb")); T = pickle.load(open(C + "/tx.pkl", "rb"))
L = [r for r in R.values() if r["dex"] == "v3" and (r["fam"]["lc"] or "").startswith("0a493d1a") and r["launch"]["selector"] == "ac9650d8"
     and r["launch"]["calldata_len"] == 836 and r["fee"] == 100 and r["launch"]["value_eth"] == 0]
shape = defaultdict(Counter); ex = {}; withval = Counter(); n_tx = Counter()
for r in L:
    o = E[r["pool"]]; qs = r["quote_side"]
    for e in o["ev"]:
        if e[0] != "s": continue
        dq = e[7] if qs == 0 else e[8]
        kind = "realbuy" if dq >= 5e15 else ("buy" if dq > 0 else "sell")
        t = T.get(e[-1])
        if not t: n_tx[kind + "_nofetch"] += 1; continue
        n_tx[kind] += 1
        k = (t["to"], t["selector"], t["calldata_len"], "val>0" if (t["value_wei"] or 0) > 0 else "val0", e[5])
        shape[kind][k] += 1
        if (kind, k) not in ex and t.get("input"): ex[(kind, k)] = (e[-1], t, dq, r["pool"], r["token"], qs)
print(n_tx)
for kind in ("realbuy", "buy", "sell"):
    print(f"\n== {kind}: top shapes (to, sel, len, value, swap sender)")
    for k, c in shape[kind].most_common(14): print("  ", c, k)
import json
pickle.dump(ex, open("w01_examples.pkl", "wb"))
for kind, sel in (("realbuy", None),):
    pass
# print one full example for: crowd bot contract realbuy, caf681a6 buy, caf681a6 sell
def show(kind, pred):
    for (kd, k), v in ex.items():
        if kd == kind and pred(k):
            h, t, dq, pool, tok, qs = v
            print(f"\n-- {kind} {k} tx {h} pool {pool} token {tok} qs {qs} dq {dq} value {t['value_wei']} gas {t.get('gas')} gp {t.get('gas_price')} prio {t.get('max_prio')} bn {t['bn']} from {t['from']}")
            inp = t["input"]; print("   ", inp[:10]); b = inp[10:]
            for i in range(0, len(b), 64): print(f"    w{i//64:02d} {b[i:i+64]}")
            return
show("realbuy", lambda k: k[1] == "3593564c" and k[2] == 484)
show("realbuy", lambda k: k[0].startswith("0xcaf681a6"))
show("sell", lambda k: k[0].startswith("0xcaf681a6"))
show("sell", lambda k: k[1] == "3593564c")
