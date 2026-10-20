"""C-1 (ETH + WETH): is there an early signal (by +40, before any price move) of whether the buyer bot 0xd6d35b56 will come?
Compares launch nonce, launch gas/tip, early swap fingerprints (first 12 swaps with offset < 40) in pools with and without a first real buy."""
from cands import *
rows = rows_nonvbot()
rs = [r for r in rows if CANDS["C1_eth"](r) or CANDS["C1_weth"](r)]
def has(r): return bool(r.get("frb"))
def show(feat, fn):
    g = C.defaultdict(lambda: [0, 0])
    for r in rs:
        k = fn(r); g[k][0] += 1; g[k][1] += has(r)
    items = sorted(g.items(), key=lambda kv: -kv[1][0])[:8]
    print(f"{feat}: " + "; ".join(f"{k}: n={v[0]} frb={v[1]/v[0]:.2f}" for k, v in items))
show("quote", lambda r: r["quote"])
show("launch nonce", lambda r: r["launch"]["nonce"])
show("launch max_prio", lambda r: r["launch"]["max_prio"])
show("launch type", lambda r: r["launch"]["type"])
show("day", lambda r: day_of(r))
show("hour-of-day UTC", lambda r: int(r["launch_utc"][11:13]) // 4 * 4)
show("token size", lambda r: r["token_code"]["size"])
show("tokm family top", lambda r: r["fam"]["tokm"][:8])
show("swap fps before +40", lambda r: tuple(sorted({f"{s[4][:8]}:{s[5]}" for s in r["swaps12"] or [] if s[0] < 40})))
show("n swaps before +40", lambda r: sum(1 for s in r["swaps12"] or [] if s[0] < 40))
show("n buys before +60 (events)", lambda r: min(5, sum(1 for b in r["first_buys"] if b[0] < 60)))
