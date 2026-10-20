import json, time, collections
from chain import *
DUST = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
head = int(rpc("eth_blockNumber", []), 16)
inits = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, 83394000, head)
pools = {l["topics"][1]: (int(l["blockNumber"], 16), l) for l in inits}
pids = sorted(pools, key=lambda p: pools[p][0]); cand = []
for i in range(0, len(pids), 60):
    bt = pids[i:i+60]; lo = min(pools[p][0] for p in bt); hi = min(max(pools[p][0] for p in bt) + 12, head)
    for a in range(lo, hi + 1, 99999):
        for l in logs({"address": PM, "topics": [T_SWAP, bt]}, a, min(a + 99998, hi)):
            bn = int(l["blockNumber"], 16); a0 = sgn(W(l["data"], 0)); a0 = a0 - (1 << 128) if a0 >= (1 << 127) else a0
            if bn - pools[l["topics"][1]][0] <= 10 and a0 < 0 and -a0 < 1e13: cand.append((l["topics"][1], l["transactionHash"], bn))
txs = batch([("eth_getTransactionByHash", [h]) for _, h, _ in cand])
hit = [(pid, bn) for (pid, h, bn), t in zip(cand, txs) if t and t["from"].lower() == DUST]
print(len(cand), "tiny early buys;", len(hit), "by the operator's dust wallet")
lt = batch([("eth_getTransactionByHash", [pools[pid][1]["transactionHash"]]) for pid, _ in hit])
bts = batch([("eth_getBlockByNumber", [hex(pools[pid][0]), False]) for pid, _ in hit])
by = collections.Counter()
for (pid, bn), t, b in zip(hit, lt, bts):
    d = pools[pid][1]["data"]
    by[(t["to"].lower(), t["input"][:10])] += 1
    print(f"  {time.strftime('%H:%M:%S', time.gmtime(int(b['timestamp'], 16)))} pool {pid[:12]} fee {W(d, 0)/1e4:.4g}% tick {sgn(W(d,1))} hook {d[2+64*2+24:2+64*3][-6:]} launched by tx to {t['to'][:12]} sel {t['input'][:10]} from {t['from'][:10]} nonce {int(t['nonce'],16)}")
print("launch contract / selector:", by.most_common())
