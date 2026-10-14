"""Where the decoy/fronter routers trade since the stop: per router, swaps per 6 h, and the share in pools launched since the stop (t04)
at launch + 0..+3 (the fronting seat), the launch families of those pools (value from t05 when known, else fee/ts) and the buy sizes."""
from common import *
import collections
sw = jl(J("t11_swaps_cache.jsonl"))
inits = {r["pid"]: r for r in jl(J("t04_inits_cache.jsonl"))}
names = {DECOY_R: "decoyR 0x65050a9b", FRONT_R2: "frontR2 0xfd1b271f", RELAY: "our relay"}
for s, nm in names.items():
    rows = [r for r in sw if r["s"] == s]
    print("==", nm, "swaps", len(rows))
    per = collections.Counter((r["b"] - 86314100) // 216000 for r in rows); print("  per 6h-bin", sorted(per.items()))
    early = collections.Counter(); fam = collections.Counter(); offs = collections.Counter(); sizes = collections.defaultdict(list)
    for r in rows:
        i = inits.get(r["pid"])
        if not i: continue
        off = r["b"] - i["b"]
        a0 = int(r["a0"]); eth_in = -a0 / 1e18 if i["c0"] == ZERO and a0 < 0 else 0
        key = (i["c0"] == ZERO, i["fee"], i["ts"], i["sqrtP"] if i["c0"] == ZERO else 0)
        if off <= 3 and eth_in > 0:
            early[key] += 1; sizes[key].append(round(eth_in, 6)); offs[off] += 1
        fam[key] += 1
    print("  buys at launch+0..3 by (ETH pair, fee, ts, sqrtP):")
    for k, n in early.most_common(12): print("    ", k, n, "sizes p50", pct(sizes[k], .5), "min", min(sizes[k]), "max", max(sizes[k]))
    print("  offsets of those", sorted(offs.items()))
    print("  all swaps in new pools by family (top):", fam.most_common(6))
