"""latest nonce (eth_getTransactionCount 'latest') for the collector and every wallet that sent to it after the last copy pull,
compared with the nonce of their last known tx (to the collector): any later outgoing tx shows up as a higher nonce"""
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from lib2 import *
C = "0x3fc5b8b8dada622d7f41a35a0ad8ac2e5d0f8d8a"
rs = touching([C], 83481000, 83518499, cached_only=True)
last = {}
for r in rs:
    if r["to"] == C: last[r["from"]] = max(last.get(r["from"], -1), r["nonce"])
extra = {C: 789, "0x1d18f10325a5b4fa584dbad259473107a29a79ac": 0, "0xe50dd00a357018225b86e232e5cb8b762b533556": 29,
         "0x58fc6f17ea0d2e472867fed709cedb6b131a40dc": 29, "0xded28cc0001917222aa2b55ad55f1d236ef1be74": 0}
last.update(extra)
addrs = sorted(last)
res = {}
for i in range(0, len(addrs), 50):
    ch = addrs[i:i + 50]
    r = gentle_post([{"jsonrpc": "2.0", "id": j, "method": "eth_getTransactionCount", "params": [a, "latest"]} for j, a in enumerate(ch)])
    for x in r:
        if "result" in x: res[ch[x["id"]]] = int(x["result"], 16)
head = int(gentle_post({"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []})["result"], 16)
bal = gentle_post([{"jsonrpc": "2.0", "id": j, "method": "eth_getBalance", "params": [a, "latest"]} for j, a in enumerate(extra)])
print("head", head, "answered", len(res), "of", len(addrs))
for x in sorted(bal, key=lambda x: x["id"]): print("  balance", list(extra)[x["id"]], int(x["result"], 16) / 1e18)
d = collections.Counter(res[a] - last[a] - 1 for a in res)
print("later outgoing txs (latest nonce - last known nonce - 1):", sorted(d.items()))
for a in extra: print("  ", a, "last known n", last[a], "latest nonce", res.get(a))
odd = [(a, last[a], res[a]) for a in res if res[a] - last[a] - 1 != 0]
print("wallets with later txs:", odd[:30])
json.dump({"head": head, "latest": res, "last_known": last}, open("latest.json", "w"))
print(bc.STATS)
