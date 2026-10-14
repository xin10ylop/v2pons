"""Step 2: every Swap and ModifyLiquidity log of the direct-launch pools, from the first launch to the head (cache: s02_events_cache.jsonl)."""
from common import *
d = jload("s01_inits.json"); dr = d["direct"]
pids = [c["pid"] for c in dr]
a0 = min(c["block"] for c in dr)
done = [r for fp in sorted(_glob.glob(os.path.join(HERE, "s02_events_*_cache.jsonl"))) for r in jl_load(os.path.basename(fp))]
last = max([r["_to"] for r in done if "_to" in r] or [a0 - 1])
head = int(rpc.call("eth_blockNumber", []), 16)
a = last + 1; step = 25000; n = 0
while a <= head:
    b = min(a + step - 1, head)
    ls = rpc.logs({"address": PM, "topics": [[T_SWAP, T_ML], pids]}, a, b)
    rows = [dict(pid=l["topics"][1], t=("S" if l["topics"][0] == T_SWAP else "M"), sender="0x" + l["topics"][2][-40:], bn=int(l["blockNumber"], 16),
                 li=int(l["logIndex"], 16), tx=l["transactionHash"], ti=int(l["transactionIndex"], 16), data=l["data"]) for l in ls]
    jl_append(rows + [{"_to": b}], "s02_events_99_cache.jsonl"); n += len(rows)
    a = b + 1
print("head", head, "new rows", n, rpc.STATS)
ev = load_events()
import collections
print("total", len(ev), collections.Counter(r["t"] for r in ev))
jdump(dict(head=head), "s02_head.json")
