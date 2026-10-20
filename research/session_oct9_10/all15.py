import json, collections, time
from chain import *
D = json.load(open("oct8.json")); pools = D["pools"]; ev = D["ev"]
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
pids = sorted(pools, key=lambda p: pools[p]["bn"])
bts = batch([("eth_getBlockByNumber", [hex(pools[p]["bn"]), False]) for p in pids])
for pid, b in zip(pids, bts):
    p = pools[pid]; b0 = p["bn"]; ls = sorted(ev.get(pid, []), key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    sw = [(int(l["blockNumber"], 16) - b0, s128(W(l["data"], 0)), l["topics"][2][-40:]) for l in ls if l["topics"][0] == T_SWAP]
    real = [x for x in sw if x[1] <= -2e14]
    pulls = [int(l["blockNumber"], 16) - b0 for l in ls if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0]
    first = real[0][0] if real else None; pull = pulls[0] if pulls else None
    nb = sum(1 for x in real if pull is None or x[0] <= pull); eth = sum(-x[1] for x in real if pull is None or x[0] <= pull) / 1e18
    ours = any(x[2] == RELAY for x in sw)
    print(f"{time.strftime('%H:%M:%S', time.gmtime(int(b['timestamp'],16)))} fee {p['fee']/1e4:7.4g}% dep {p['deployer'][:8]} first real buy +{first} pull +{pull} pull-first {str(None if first is None or pull is None else pull-first):>5} buys before pull {nb:3d} ({eth:.3f} ETH) {'<== OURS' if ours else ''} senders {collections.Counter(x[2][:6] for x in sw).most_common(3)}")
