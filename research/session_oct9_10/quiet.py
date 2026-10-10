import json, time, collections
from chain import *
b = rpc("eth_getBlockByNumber", ["latest", False]); head = int(b["number"], 16)
print("chain now", time.strftime("%H:%M UTC", time.gmtime(int(b["timestamp"], 16))), "block", head)
# 1. launches through the operator's launcher since 14:45
inits = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, 83394000, head)
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
to = collections.Counter((t.get("to") or "")[2:].lower() for t in txs if t)
print("ETH pools since 14:45:", len(inits), "| by launcher:", [(a[:10], n) for a, n in to.most_common(8)])
print("via the operator's launcher 0x3194e326:", to.get(OP, 0))
# 2. the dust wallet that buys every operator launch at +3/+4: where is it now?
D = json.load(open("oct8.json")); ev = D["ev"]
h = next(l["transactionHash"] for ls in ev.values() for l in ls if l["topics"][0] == T_SWAP)
dust = None
for ls in ev.values():
    for l in ls:
        if l["topics"][0] == T_SWAP:
            t = rpc("eth_getTransactionByHash", [l["transactionHash"]])
            if t["from"].lower().startswith("0xe71a69f4"): dust = t["from"]; break
    if dust: break
n = int(rpc("eth_getTransactionCount", [dust, "latest"]), 16)
print("dust wallet", dust, "nonce now", n, "(91,020 on the 14:32 launch)")
