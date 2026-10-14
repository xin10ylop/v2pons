"""s03: every log each family token emitted, ALL topics (Transfer, Approval, OwnershipTransferred, Initialized and anything unknown),
from its launch block to the head. address-filtered getLogs over sentio/blockmachine, 10k-block chunks (sentio returns null and blockmachine refuses above 10,000), split on error.
-> data/toklogs_cache.jsonl (one row per token: token, from, to, logs [b, ti, li, tx, topics, data])"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))
import rpc
D = os.path.join(os.path.dirname(__file__), "..", "data")
F = json.load(open(os.path.join(D, "s02_family.json")))
toks = F["family"] + ([r for r in F["all_v7"] if r not in F["family"]] if "--all" in sys.argv else [])
HEAD = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else min(int(rpc.call("eth_blockNumber", [], urls=[u]), 16) for u in rpc.HIST)
cache = os.path.join(D, "toklogs_cache.jsonl"); have = set()
if os.path.exists(cache):
    for l in open(cache): have.add(json.loads(l)["token"])
fh = open(cache, "a")
for n, r in enumerate(toks):
    t = r["token"]
    if t in have: continue
    out = []; cur = r["b"]; ch = 10000
    while cur <= HEAD:
        end = min(HEAD, cur + ch - 1)
        try:
            L = rpc.logs(t, [], cur, end)
            if L is None: raise rpc.RPCError("null result")
        except rpc.RPCError as e:
            if ch <= 500: print("fail", t, cur, str(e)[:100]); time.sleep(3); continue
            ch //= 4; continue
        out += [[int(x["blockNumber"], 16), int(x["transactionIndex"], 16), int(x["logIndex"], 16), x["transactionHash"], x["topics"], x["data"]] for x in L]
        cur = end + 1; ch = min(10000, ch * 2)
    fh.write(json.dumps({"token": t, "from": r["b"], "to": HEAD, "logs": out}) + "\n"); fh.flush()
    if n % 10 == 0: print(n, t, len(out), flush=True)
print("done", HEAD)
