import sys, json, calendar, time, collections
from chain import *
t_lo = calendar.timegm(time.strptime("2026-10-08 11:30", "%Y-%m-%d %H:%M"))
b_lo = block_at(t_lo); head = int(rpc("eth_blockNumber", []), 16)
print("blocks", b_lo, head, "head ts", time.strftime("%H:%M:%S", time.gmtime(int(rpc("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16))), flush=True)
inits = []
for a in range(b_lo, head, 99999):
    inits += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, a, min(a + 99998, head))
print(len(inits), "ETH inits", flush=True)
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
pools = {}
for l, t in zip(inits, txs):
    if t and (t.get("to") or "")[2:].lower() == OP:
        d = l["data"]; pools[l["topics"][1]] = {"bn": int(l["blockNumber"], 16), "tx": l["transactionHash"], "token": l["topics"][3][-40:], "fee": W(d, 0), "ts_sp": sgn(W(d,1)), "hooks": d[2+64*2+24:2+64*3], "sqrtP0": W(d, 3), "tick0": sgn(W(d, 4)), "deployer": t["from"][2:].lower()}
print(len(pools), "operator launches", flush=True)
pids = sorted(pools, key=lambda p: pools[p]["bn"])
ev = collections.defaultdict(list)
for i in range(0, len(pids), 60):
    bt = pids[i:i+60]; lo = min(pools[p]["bn"] for p in bt); hi = min(max(pools[p]["bn"] for p in bt) + 12000, head)
    for a in range(lo, hi, 99999):
        for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], bt]}, a, min(a + 99998, hi)):
            ev[l["topics"][1]].append(l)
json.dump({"pools": pools, "ev": ev, "range": [b_lo, head]}, open("oct8.json", "w"))
nonrouter = collections.Counter()
for pid, ls in ev.items():
    for l in ls:
        if l["topics"][0] == T_SWAP and l["topics"][2][-40:] != UR: nonrouter[l["topics"][2][-40:]] += 1
print("non-router swap senders:", nonrouter.most_common(20))
