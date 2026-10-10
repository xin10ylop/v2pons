"""a few targeted RPC reads the census cannot answer (cached in rpc_cache.json):
 - the txs that added the liquidity of family 3 (Initialize straight on the PoolManager, liquidity added later)
 - receipts of a few swaps on the hook pools (families 2 and 4) to measure what the hook takes beyond the LP fee"""
import sys, os, json
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from chain import batch
from load import *
HERE = os.path.dirname(os.path.abspath(__file__)); CF = os.path.join(HERE, "rpc_cache.json")
cache = json.load(open(CF)) if os.path.exists(CF) else {}
F = load_families(); P = load_pools()
K2 = "0x5bd1fbe78a78fe8236fa00cf48fbeba74ae34661|a80ac0c2|1156|0|200|false"
K3 = "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|3000|60|true"
K4 = "0xa0ce0291c181f800e7a5096b433685c37cfbf4df|617ac5de|676|8388608|200|false"
E = load_events(set(F[K2]["pids"] + F[K3]["pids"] + F[K4]["pids"]))
want_tx, want_rc = set(), set()
for pid in F[K3]["pids"]:
    for a in E[pid]["adds"]: want_tx.add(a["tx"]); want_rc.add(a["tx"])
    for s in E[pid]["swaps"]: want_rc.add(s["tx"])
for pid in F[K2]["pids"] + F[K4]["pids"]:
    for s in E[pid]["swaps"][:12]:
        want_rc.add(s["tx"]); want_tx.add(s["tx"])
calls = [("eth_getTransactionByHash", [h]) for h in sorted(want_tx) if "tx:" + h not in cache] + \
        [("eth_getTransactionReceipt", [h]) for h in sorted(want_rc) if "rc:" + h not in cache]
print(len(calls), "calls")
res = batch(calls) if calls else []
for (m, p), r in zip(calls, res):
    cache[("tx:" if m == "eth_getTransactionByHash" else "rc:") + p[0]] = r
json.dump(cache, open(CF, "w"))
print(len(cache), "cached;", sum(1 for v in cache.values() if v is None), "null")
