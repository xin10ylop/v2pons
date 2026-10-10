import time, collections
from chain import *
W_ = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
b = rpc("eth_getBlockByNumber", ["latest", False]); head = int(b["number"], 16)
print("chain now", time.strftime("%H:%M:%S UTC", time.gmtime(int(b["timestamp"], 16))), "| wallet nonce", int(rpc("eth_getTransactionCount", [W_, "latest"]), 16))
inits = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, 83479000, head)
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
print("ETH pools since 17:11:", len(inits), "| with the operator's call 0x2fcb9108:", sum(1 for t in txs if t and t["input"][:10] == "0x2fcb9108"))
# the burst signature on any pool, whatever the launch call: two or more real buys by brand-new wallets in one block, within 20 blocks of the launch
pools = {l["topics"][1]: (int(l["blockNumber"], 16), l, t) for l, t in zip(inits, txs) if t}
pids = list(pools); early = []
for i in range(0, len(pids), 60):
    bt = pids[i:i+60]; lo = min(pools[p][0] for p in bt); hi = min(max(pools[p][0] for p in bt) + 300, head)
    for a in range(lo, hi + 1, 99999):
        for l in logs({"address": PM, "topics": [T_SWAP, bt]}, a, min(a + 99998, hi)):
            d = l["data"]; a0 = sgn(W(d, 0)); a0 = a0 - (1 << 128) if a0 >= (1 << 127) else a0
            if int(l["blockNumber"], 16) - pools[l["topics"][1]][0] <= 300 and a0 <= -2e14: early.append((l["topics"][1], int(l["blockNumber"], 16), l["transactionHash"]))
et = batch([("eth_getTransactionByHash", [h]) for _, _, h in early])
burst = collections.defaultdict(list)
for (p, bn, h), t in zip(early, et):
    if t and int(t["nonce"], 16) == 0: burst[(p, bn)].append(t)
hits = [(p, bn, ts) for (p, bn), ts in burst.items() if len(ts) >= 2]
print("pools with a fresh-wallet burst in their first 300 blocks:", len(hits))
for p, bn, ts in sorted(hits, key=lambda x: x[1]):
    b0, l, t = pools[p]; d = l["data"]
    print(f"   launch {b0} fee {W(d,0)/1e4:.3f}% tick {sgn(W(d,1))} burst at +{bn-b0} ({len(ts)} buys) launched by tx to {t['to'][:10]} call {t['input'][:10]} from nonce {int(t['nonce'],16)}")
