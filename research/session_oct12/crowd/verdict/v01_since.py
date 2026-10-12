"""Read-only: v3crowd-shaped launches (NPM 836-byte value-0 multicall, fee 100, WETH side) after block 86,743,912 (the last one, 13:44 UTC Oct 12) to the head.
Public RPC only, paced through ../replay/rpc.py. Prints counts and times; writes nothing but its own rpc log."""
import sys, os, json, time, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "replay"))
from common import FACT, NPM, WETH, T_PC, utc
import rpc
FROM = 86743912
head = int(rpc.call("eth_blockNumber", []), 16); th = int(rpc.call("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
print("head", head, utc(th))
pc = []
for a in range(FROM, head + 1, 200000):
    pc += rpc.logs({"address": FACT, "topics": [T_PC]}, a, min(a + 199999, head))
cand = [l for l in pc if int(l["topics"][3], 16) == 100 and WETH[2:] in (l["topics"][1][-40:], l["topics"][2][-40:])]
print("PoolCreated", len(pc), "fee100+WETH", len(cand))
txs = rpc.batch("eth_getTransactionByHash", [[l["transactionHash"]] for l in cand]) if cand else []
sh = collections.Counter(); hits = []
for l, t in zip(cand, txs):
    to = (t.get("to") or "").lower(); n = (len(t["input"]) - 2) // 2; v = int(t["value"], 16)
    k = (to[:10], t["input"][2:10], n, v > 0); sh[k] += 1
    if to == NPM and t["input"][:10] == "0xac9650d8" and n == 836 and v == 0: hits.append(int(l["blockNumber"], 16))
for b in hits:
    print("v3crowd launch", b, utc(int(rpc.call("eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)))
print("v3crowd-shaped since 13:44:", len(hits)); print("shapes:", sh.most_common(10)); print("rpc", rpc.STATS)
