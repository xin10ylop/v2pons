import sys, time, collections
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
from chain import *
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"; WAL = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
head = int(rpc("eth_blockNumber", []), 16); START = head - int(25 * 60 / 0.103)
ours = logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0" * 24 + RELAY]}, START, head)
print("relay swaps since Oct 8 17:11:", len(ours))
pids = sorted({l["topics"][1] for l in ours}, key=lambda p: min(int(l["blockNumber"], 16) for l in ours if l["topics"][1] == p))
for pid in pids:
    il = logs({"address": PM, "topics": [T_INIT, pid]}, START - 3000, head)[0]; b0 = int(il["blockNumber"], 16); fee = W(il["data"], 0)
    lt = rpc("eth_getTransactionByHash", [il["transactionHash"]]); ts = int(rpc("eth_getBlockByNumber", [hex(b0), False])["timestamp"], 16)
    ls = sorted(logs({"address": PM, "topics": [[T_SWAP, T_ML], pid]}, b0, min(b0 + 3000, head)), key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    T = dict(zip([l["transactionHash"] for l in ls], batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in ls])))
    print(f"\n=== pool {pid[:12]} launched {time.strftime('%m-%d %H:%M:%S', time.gmtime(ts))} UTC, fee {fee/1e4:.3f}%, launch call {lt['input'][:10]} to {lt['to'][:10]}")
    mine = [l for l in ls if l["topics"][0] == T_SWAP and l["topics"][2][-40:] == RELAY]
    B = int(mine[0]["blockNumber"], 16)
    for l in ls:
        bn = int(l["blockNumber"], 16)
        if bn > B + 12 and l["topics"][0] == T_SWAP: continue
        t = T[l["transactionHash"]]; d = l["data"]
        if l["topics"][0] == T_SWAP:
            a0 = s128(W(d, 0)); a1 = s128(W(d, 1)); who = "US   " if l["topics"][2][-40:] == RELAY else "     "
            print(f"  +{bn-b0:4d} (buy{bn-B:+4d}) idx {int(t['transactionIndex'],16):3d} {who}{'buy ' if a0 < 0 else 'sell'} {abs(a0)/1e18:.6f} ETH  tokens {abs(a1):.4e}  from {t['from'][:10]} nonce {int(t['nonce'],16)}")
        else:
            dl = sgn(W(d, 2)); print(f"  +{bn-b0:4d} (buy{bn-B:+4d}) idx {int(t['transactionIndex'],16):3d} {'ADD ' if dl > 0 else 'PULL'} liquidity  from {t['from'][:10]}")
    if len(mine) >= 2:
        a0b = -s128(W(mine[0]["data"], 0)); a0s = s128(W(mine[1]["data"], 0))
        print(f"  RESULT: paid {a0b/1e18:.6f} ETH, got back {a0s/1e18:.6f} ETH -> {100*(a0s-a0b)/a0b:+.2f}% before gas")
