"""All fee-100 WETH V3 pools of the last 8 h by launch shape and hour (did the line move to another shape?)"""
import json, sys, os, time
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpc
from eth_utils import keccak
D = json.load(open("w05_recent_8h.json")); head, start, t_head, bps = D["head"], D["start"], D["t_head"], D["bps"]
FACT = "0x1f7d7550b1b028f7571e69a784071f0205fd2efa"; WETH = "0bd7d308f8e1639fab988df18a8011f41eacad73"
T_PC = "0x" + keccak(text="PoolCreated(address,address,uint24,int24,address)").hex()
pc = []
for a in range(start, head + 1, 50000): pc += rpc.logs({"address": FACT, "topics": [T_PC]}, a, min(a + 49999, head))
txs = rpc.batch("eth_getTransactionByHash", [[l["transactionHash"]] for l in pc])
by = defaultdict(Counter); fee = Counter()
for l, t in zip(pc, txs):
    f = int(l["topics"][3], 16); weth = WETH in (l["topics"][1][-40:], l["topics"][2][-40:])
    shape = ((t.get("to") or "")[:10], t["input"][:10], (len(t["input"]) - 2) // 2, int(t["value"], 16) > 0) if t else None
    hr = time.strftime("%H", time.gmtime(t_head - (head - int(l["blockNumber"], 16)) / bps))
    by[(f, weth, shape)][hr] += 1
for k, v in sorted(by.items(), key=lambda kv: -sum(kv[1].values())):
    print(sum(v.values()), k, dict(sorted(v.items())))
print(rpc.STATS)
