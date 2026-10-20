"""Check v3exact against the chain: each r01 pool from its launch (Initialize at the decoded sqrtP, the decoded Mint), then every logged
Mint/Burn applied and every Swap re-simulated by its input amount (exact input); compare amount0, amount1, sqrtPriceX96, liquidity, tick
with the Swap event. Swaps checked up to launch + WIN (r02's window). Writes r04_validate.out."""
from common import *
import collections
from v3exact import Pool
X = json.load(open(J("r01_launches.json"))); ev = jl(J("r02_events_cache.jsonl")); by = collections.defaultdict(list)
for e in ev: by[e["a"]].append(e)
WIN = json.load(open(J("r02_meta.json")))["win"]
tot = collections.Counter(); bad = []
for x in X:
    p = Pool(x["sqrt_p"]); es = by[x["pool"]]; broke = False
    for e in es:
        if e["bn"] - x["lb"] > WIN: break
        k = e["t"][0]
        if k == T_MI:
            p.modify("0x" + e["t"][1][-40:], sgn(int(e["t"][2], 16)), sgn(int(e["t"][3], 16)), W(e["d"], 1)); tot["mint"] += 1
        elif k == T_BU:
            p.modify("0x" + e["t"][1][-40:], sgn(int(e["t"][2], 16)), sgn(int(e["t"][3], 16)), -W(e["d"], 0)); tot["burn"] += 1
        elif k == T_SW:
            a0, a1 = sgn(W(e["d"], 0)), sgn(W(e["d"], 1)); sp, L, tk = W(e["d"], 2), W(e["d"], 3), sgn(W(e["d"], 4))
            zfo = a0 > 0
            q = p.copy(); r = q.swap(zfo, a0 if zfo else a1)
            ok = r == (a0, a1) and q.sp == sp and q.L == L and q.tick == tk
            if ok: tot["swap_exact"] += 1; p = q
            else:
                tot["swap_diff"] += 1
                if len(bad) < 15: bad.append((x["pool"][:10], e["bn"] - x["lb"], e["tx"][:12], (a0, a1), r, sp - q.sp, L - q.L, tk - q.tick))
                p.sp, p.L, p.tick = sp, L, tk          # resync to the chain (an exact-output swap or a price limit)
                p = p
print(dict(tot)); [print(b) for b in bad]
