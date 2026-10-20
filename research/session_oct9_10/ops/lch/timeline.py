import json, sys, collections, time, statistics as st, bisect
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import batch
R = json.load(open("population.json"))
try: TS = {int(k): v for k, v in json.load(open("bts.json")).items()}
except Exception: TS = {}
pts = list(range(19_000_000, 84_200_000, 250_000))
need = [b for b in pts if b not in TS]
if need:
    res = batch([("eth_getBlockByNumber", [hex(b), False]) for b in need])
    for b, r in zip(need, res):
        if r: TS[b] = int(r["timestamp"], 16)
    json.dump(TS, open("bts.json", "w"))
ks = sorted(TS)
def ts(bn):
    i = bisect.bisect_right(ks, bn) - 1; i = max(0, min(i, len(ks) - 2)); a, b = ks[i], ks[i + 1]
    return TS[a] + (TS[b] - TS[a]) * (bn - a) / (b - a)
for r in R: r["t"] = ts(r["bn"]); r["day"] = time.strftime("%m-%d", time.gmtime(r["t"])); r["wk"] = time.strftime("%Y-W%W", time.gmtime(r["t"]))
json.dump(R, open("population.json", "w"))
g = collections.defaultdict(list)
for r in R: g[r["wk"]].append(r)
print("week      n  nonce0  reused  tip.02 tip.1  medETH  medFee  supply1e9  senders>1(in wk)")
for k in sorted(g):
    v = g[k]; c = collections.Counter(x["frm"] for x in v)
    print(f"{k} {len(v):5d} {sum(x['nonce']==0 for x in v):6d} {sum(x['nonce']>0 for x in v):6d} {sum(x['tip']==20000000 for x in v):6d} {sum(x['tip']==100000000 for x in v):5d} {st.median(x['eth'] for x in v):7.3f} {st.median(x['fee'] for x in v):7.0f} {sum(x['supply']==10**27 for x in v):9d} {sum(1 for a,n in c.items() if n>1):5d}")
