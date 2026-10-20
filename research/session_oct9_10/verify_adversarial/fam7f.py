import sys, json, collections, time; sys.path.insert(0, "..")
from chain import *
D = json.load(open("newsch.json")); P, head = D["P"], D["head"]
last = max(P[q]["b0"] for q in P)
inits = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}, last + 1, head)
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in inits])
F = [(l, t) for l, t in zip(inits, txs) if t["input"][:10] == "0x7fde822e" and l["data"][2+64*2+24:2+64*3] == "0"*40]
print("0x7fde822e launches", len(F))
deps = collections.Counter(t["from"][:10] for l, t in F); print("senders", deps.most_common(6))
noncs = [int(t["nonce"],16) for l, t in F]; print("sender nonces sample", noncs[:10])
pids = [l["topics"][1] for l, t in F][:12]
bts = batch([("eth_getBlockByNumber", [l["blockNumber"], False]) for l, t in F[:12]])
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
for (l, t), b in zip(F[:12], bts):
    b0 = int(l["blockNumber"], 16); pid = l["topics"][1]
    ls = logs({"address": PM, "topics": [[T_SWAP, T_ML], pid]}, b0, min(b0 + 6000, head))
    sw = [(int(x["blockNumber"],16)-b0, s128(W(x["data"],0))/1e18) for x in ls if x["topics"][0] == T_SWAP]
    ml = [(int(x["blockNumber"],16)-b0, sgn(W(x["data"],2))) for x in ls if x["topics"][0] == T_ML]
    pulls = [m[0] for m in ml if m[1] < 0]
    print(time.strftime('%H:%M:%S', time.gmtime(int(b['timestamp'],16))), "from", t["from"][:10], "to", t["to"][:10], "buys", [(a, round(-v,4)) for a, v in sw if v < 0][:6], "nbuys", sum(1 for a,v in sw if v<0), "pull", pulls[:1])
