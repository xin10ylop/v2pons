"""C-1 ETH: token price move (%) from before the first real buy to the end of its block, to the end of the next block (the burst), and to frb+62."""
from cands import *
from replay import prep, state_before
rows = rows_nonvbot(); E = load_ev()
rs = [r for r in rows if CANDS["C1_eth"](r) and r.get("frb")]
m0, m1, m62 = [], [], []
for r in rs:
    P = prep(r, E[r["pool"]]); f = P["lb"] + r["frb"]["off"]
    s0 = state_before(P, f)[0]
    for lst, blk in ((m0, f + 1), (m1, f + 2), (m62, f + 63)):
        if any(p < blk for p in P["pulls"]): continue
        s = state_before(P, blk)[0]; lst.append(100 * ((s0 / s) ** 2 - 1))
print("C1_eth price move % from before the first real buy: to end of its block", p1050(m0), "; to end of next block", p1050(m1), "; to frb+62 (unpulled)", p1050(m62), "n", len(m0), len(m62))
