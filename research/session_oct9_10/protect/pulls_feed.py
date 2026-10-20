"""Can the engine see each pull in the feed and tie it to its pool? For every pull (first negative ModifyLiquidity) on the 143
operator launches: the pull tx's to, selector, and whether the pool's token address is in its calldata. Writes pulls_feed.json."""
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from load_all import *
from chain import batch
pools, head = load_all()
pp = [p for p in pools if p["pull"]]
txs = batch([("eth_getTransactionByHash", [p["pull"]["tx"]]) for p in pp])
res = collections.Counter(); rows = []
for p, t in zip(pp, txs):
    tok = (p["m"].get("token") or "").lower()
    inp = t["input"].lower()
    r = {"pid": p["pid"][:10], "kind": p["kind"], "to": t["to"], "sel": inp[:10], "len": len(inp) // 2 - 1, "token_in_calldata": tok in inp, "gas": int(t["gas"], 16),
         "prio": int(t.get("maxPriorityFeePerGas", "0x0"), 16), "from_is_deployer": t["from"].lower() == p["deployer"], "value": int(t["value"], 16)}
    rows.append(r); res[(r["to"][:10], r["sel"], r["token_in_calldata"], r["from_is_deployer"], r["len"], r["gas"], r["prio"])] += 1
for k, v in res.most_common(): print(v, k)
json.dump(rows, open(HERE + "pulls_feed.json", "w"), indent=0)
