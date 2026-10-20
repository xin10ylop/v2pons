import json, sys, collections, statistics as st
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
from chain import *
rows = json.load(open("newlaunch.json"))[1:]
head = int(rpc("eth_blockNumber", []), 16)
pids = [p for p, _ in rows]; b0s = dict(rows); ev = {p: [] for p in pids}
for i in range(0, len(pids), 40):
    bt = pids[i:i+40]; lo = min(b0s[p] for p in bt); hi = min(max(b0s[p] for p in bt) + 2000, head)
    for a in range(lo, hi + 1, 99999):
        for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], bt]}, a, min(a + 99998, hi)): ev[l["topics"][1]].append(l)
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
early = [(p, l) for p in pids for l in ev[p] if l["topics"][0] == T_SWAP and int(l["blockNumber"], 16) - b0s[p] <= 20]
T = dict(zip([l["transactionHash"] for _, l in early], batch([("eth_getTransactionByHash", [l["transactionHash"]]) for _, l in early])))
fromcount = collections.Counter(T[l["transactionHash"]]["from"].lower() for _, l in early)
for p in pids[:6] + pids[-4:]:
    b0 = b0s[p]; print(f"\n{p[:12]} launch block {b0}")
    for l in sorted([l for q, l in early if q == p], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
        t = T[l["transactionHash"]]; a0 = s128(W(l["data"], 0))
        print(f"   +{int(l['blockNumber'],16)-b0:3d} idx {int(t['transactionIndex'],16):3d} {'buy ' if a0 < 0 else 'sell'} {abs(a0)/1e18:.5f} ETH from {t['from'][:10]} nonce {int(t['nonce'],16):5d} to {t['to'][:10]} (seen on {fromcount[t['from'].lower()]} of these launches)")
    pl = [int(l["blockNumber"], 16) - b0 for l in ev[p] if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0]
    print("   pull at +", min(pl) if pl else None)
