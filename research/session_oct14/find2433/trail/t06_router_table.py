"""Table of the router-minted tokens since the stop by launch family: value, fee/ts, sqrtP, sender nonce, calldata length, gas; per hour."""
from common import *
import collections
ins = jl(J("t02_in_cache.jsonl"))
mints = {r["tok"]: r for r in ins if r["fr"] == ZERO}
buys = collections.Counter(r["tok"] for r in ins if r["fr"] == PM)
inits = jl(J("t04_inits_cache.jsonl"))
by_tok = collections.defaultdict(list)
for i in inits:
    by_tok[i["c1"]].append(i); by_tok[i["c0"]].append(i)
ltx = {r["h"]: r for r in jl(J("t05_ltx_cache.jsonl"))}
fam = collections.Counter(); rows = []
for t, m in mints.items():
    ii = by_tok.get(t, [])
    if not ii:
        fam[("no pool", t[-3:] == "777")] += 1; rows.append((m["b"], t, None, None)); continue
    for i in ii:
        x = ltx.get(i["tx"], {})
        key = (round(int(x.get("v", 0)) / 1e18, 7), i["fee"], i["ts"], i["c0"] == ZERO, i["hooks"] != "0x" + "0" * 40, x.get("to", "")[:10], x.get("sel"), x.get("len"), x.get("gas"), t[-3:] == "777")
        fam[key] += 1; rows.append((i["b"], t, key, x))
print("tokens minted to the router since block 86314100:", len(mints))
print("families (value ETH, fee, ts, ETH-pair, hooked, to, selector, calldata len, gas limit, address ends 777): count")
for k, n in fam.most_common(): print("  ", k, n)
# sqrtP by family
sq = collections.defaultdict(collections.Counter)
for b, t, key, x in rows:
    if key:
        i = [i for i in by_tok[t]][0]; sq[key[0]][i["sqrtP"]] += 1
for v, c in sq.items(): print("value", v, "sqrtP", c.most_common(3))
# launch sender nonce by family
nn = collections.defaultdict(collections.Counter)
for b, t, key, x in rows:
    if key: nn[key[0]][x.get("nonce")] += 1
for v, c in nn.items(): print("value", v, "sender nonce", sorted(c.items())[:12], "...", len(c), "distinct")
# per 6 hours by value
per = collections.defaultdict(collections.Counter)
for b, t, key, x in rows:
    if key: per[(b - 86314100) // 216000][key[0]] += 1
for k in sorted(per): print("6h-bin", k, dict(per[k]))
print("router buys by token family:")
bf = collections.Counter()
for b, t, key, x in rows:
    bf[key[0] if key else "no pool"] += buys.get(t, 0)
print("  ", dict(bf))
