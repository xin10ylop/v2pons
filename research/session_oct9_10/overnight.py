import time, collections
from chain import *
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
head = int(rpc("eth_blockNumber", []), 16)
inits = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, 83479000, head)
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
op = [(l, t) for l, t in zip(inits, txs) if t and t["input"][:10] == "0x2fcb9108"]
bts = batch([("eth_getBlockByNumber", [l["blockNumber"], False]) for l, _ in op])
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
print(f"operator launches (call 0x2fcb9108) since Oct 8 17:11: {len(op)}")
print("  time (UTC)      fee      launcher     ours  real buys in 300 blocks (block: ETH, wallet nonce)                        pull")
for (l, t), b in zip(op, bts):
    pid = l["topics"][1]; b0 = int(l["blockNumber"], 16)
    ls = sorted(logs({"address": PM, "topics": [[T_SWAP, T_ML], pid]}, b0, min(b0 + 20000, head)), key=lambda x: (int(x["blockNumber"], 16), int(x["logIndex"], 16)))
    sw = [x for x in ls if x["topics"][0] == T_SWAP and int(x["blockNumber"], 16) - b0 <= 300 and s128(W(x["data"], 0)) <= -2e14]
    st = batch([("eth_getTransactionByHash", [x["transactionHash"]]) for x in sw]) if sw else []
    ours = any(x["topics"][0] == T_SWAP and x["topics"][2][-40:] == RELAY for x in ls)
    pulls = [int(x["blockNumber"], 16) - b0 for x in ls if x["topics"][0] == T_ML and sgn(W(x["data"], 2)) < 0]
    buys = [f"+{int(x['blockNumber'],16)-b0}: {-s128(W(x['data'],0))/1e18:.3f} n{int(y['nonce'],16)}" for x, y in zip(sw, st) if x["topics"][2][-40:] != RELAY]
    print(f"  {time.strftime('%m-%d %H:%M:%S', time.gmtime(int(b['timestamp'], 16)))}  {W(l['data'],0)/1e4:.3f}%  {t['to'][:10]}  {'YES ' if ours else '    '} {(', '.join(buys[:5]) + (' ...' if len(buys) > 5 else '')) or 'none':72s} {('+' + str(pulls[0])) if pulls else 'not yet'}")
