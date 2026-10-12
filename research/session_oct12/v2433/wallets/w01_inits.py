"""Every v4 Initialize from Oct 11 12:00 UTC to the head (logs only), cached to w01_inits_cache.jsonl; then groups by (fee, ts, sqrtP, quote, hooks)."""
from common import *
import collections
OUT = J("w01_inits_cache.jsonl"); META = J("w01_meta.json")
h, th = head()
start_ts = 1791720000  # Oct 11 12:00 UTC
done = jl(OUT); last = max([d["b"] for d in done], default=None)
if last is None:
    start = block_at(start_ts, (h, th)); print("start block", start, utc(ts_of(start)))
else: start = last + 1
with open(OUT, "a") as f:
    for a in range(start, h + 1, 50000):
        b = min(a + 49999, h)
        for l in rpc.logs({"address": PM, "topics": [T_INIT]}, a, b):
            d = l["data"]
            r = {"b": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "tx": l["transactionHash"], "pid": l["topics"][1], "c0": "0x" + l["topics"][2][-40:], "c1": "0x" + l["topics"][3][-40:],
                 "fee": W(d, 0), "ts": sgn(W(d, 1)), "hooks": "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3], "sqrtP": W(d, 3), "tick": sgn(W(d, 4))}
            f.write(json.dumps(r) + "\n")
        print("scanned", a, b, flush=True)
json.dump({"head": h, "head_ts": th}, open(META, "w"))
rows = jl(OUT)
g = collections.Counter((r["fee"], r["ts"], r["sqrtP"] == SQRTP_2433, r["c0"] == "0x" + "0" * 40, r["hooks"] == "0x" + "0" * 40) for r in rows)
print(len(rows), "inits;", g.most_common(30))
print(rpc.STATS)
