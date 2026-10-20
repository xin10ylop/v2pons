"""Per router-minted token since the stop: the bot router's first buy in blocks after the ETH launch, buys per pool and ETH-launch
sender class; per 6-hour bin and family. Also checks whether 5.0 token addresses ended in 777 before the stop (Oct 12 skeptic data)."""
from common import *
import collections
ins = jl(J("t02_in_cache.jsonl"))
mints = {r["tok"]: r for r in ins if r["fr"] == ZERO}
buys = collections.defaultdict(list)
for r in ins:
    if r["fr"] == PM: buys[r["tok"]].append(r["b"])
inits = jl(J("t04_inits_cache.jsonl"))
eth_init = {}
for i in inits:
    if i["c0"] == ZERO: eth_init.setdefault(i["c1"], i)
ltx = {r["h"]: r for r in jl(J("t05_ltx_cache.jsonl"))}
st = collections.defaultdict(lambda: collections.defaultdict(list))
for t in mints:
    i = eth_init.get(t)
    if not i: continue
    x = ltx.get(i["tx"]); v = round(int(x["v"]) / 1e18, 4)
    if v not in (3.0, 5.0): continue
    bb = sorted(buys.get(t, []))
    fb = bb[0] - i["b"] if bb else None
    k = (i["b"] - 86314100) // 216000
    st[(v, k)]["fb"].append(fb if fb is not None else 9999); st[(v, k)]["n"].append(len(bb))
print("family 6h-bin pools firstbuy p10/p50/p90  first-buy<=16  buys/pool p50  no-buy")
for (v, k) in sorted(st):
    d = st[(v, k)]; fb = [x for x in d["fb"] if x != 9999]
    print(v, k, len(d["fb"]), pct(fb, .1), pct(fb, .5), pct(fb, .9), sum(1 for x in fb if x <= 16), pct(d["n"], .5), sum(1 for x in d["fb"] if x == 9999))
