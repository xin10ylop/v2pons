"""C-1 operator router 0xd6d35b56 (selector e6cb474f, 484 bytes): word layout of every first real buy and of every later buy with that
fingerprint in the first 12 swaps: w1 recipient (== tx.from?), w2 amountIn (== swap quote amount?), w3 (min out?), w4."""
from cands import *
from load import load_txs
from replay import prep
rows = rows_nonvbot(); E = load_ev(); T = load_txs()
OPR = "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"
for name in ("C1_eth", "C1_weth"):
    rs = [r for r in rows if CANDS[name](r)]
    w3 = C.Counter(); w4 = C.Counter(); rec_from = 0; amt_eq = 0; n = 0; vals = C.Counter(); amt_ratio = []
    for r in rs:
        P = prep(r, E[r["pool"]]); hs = {w["tx"]: w for w in P["sw"]}
        for s in r.get("swaps12") or []:
            if s[4] != OPR: continue
            # find the tx of this swap: match by offset and size among P["sw"]
            cand = [w for w in P["sw"] if w["bn"] - P["lb"] == s[0] and w["buy"] == (s[1] == "B")]
            for w in cand:
                x = T.get(w["tx"])
                if not x or x["to"] != OPR: continue
                h = x.get("input_head") or ""; W = [int(h[10 + 64 * i: 10 + 64 * (i + 1)] or "0", 16) for i in range(6)]
                n += 1; w3[W[3]] += 1; w4[W[4]] += 1; vals[x["value_wei"] > 0] += 1
                if W[1] == int(x["from"], 16): rec_from += 1
                if W[2] == w["q"]: amt_eq += 1
                amt_ratio.append(w["q"] / W[2] if W[2] else None)
                break
    print(name, "operator-router buys decoded:", n, " w3 (min out?) values:", w3.most_common(4), " w4:", w4.most_common(3), " recipient==from:", rec_from,
          " amountIn==swap quote:", amt_eq, " tx carries ETH value:", dict(vals))
