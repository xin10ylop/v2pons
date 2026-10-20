import json, collections, time
from chain import *
D = json.load(open("oct8.json")); pools = D["pools"]; ev = D["ev"]
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
mine = [pid for pid, ls in ev.items() if any(l["topics"][0] == T_SWAP and l["topics"][2][-40:] == RELAY for l in ls)]
mine.sort(key=lambda p: pools[p]["bn"])
hashes = sorted({l["transactionHash"] for pid in mine for l in ev[pid]})
T = dict(zip(hashes, batch([("eth_getTransactionByHash", [h]) for h in hashes])))
for k, pid in enumerate(mine, 1):
    p = pools[pid]; b0 = p["bn"]; ls = sorted(ev[pid], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    ts = int(rpc("eth_getBlockByNumber", [hex(b0), False])["timestamp"], 16)
    print(f"\n=== trade {k} pool {pid[:12]} fee {p['fee']/1e4:g}% launch blk {b0} {time.strftime('%H:%M:%S', time.gmtime(ts))} deployer {p['deployer'][:10]} token {p['token'][:10]}")
    ours = [int(l["blockNumber"], 16) for l in ls if l["topics"][0] == T_SWAP and l["topics"][2][-40:] == RELAY]
    bb = ours[0]
    for l in ls:
        bn = int(l["blockNumber"], 16); t = T[l["transactionHash"]]; d = l["data"]
        if bn > bb + 40: break
        frm = t["from"][2:12]; idx = int(t["transactionIndex"], 16); nonce = int(t["nonce"], 16)
        if l["topics"][0] == T_SWAP:
            a0 = s128(W(d, 0)); a1 = s128(W(d, 1)); who = "RELAY" if l["topics"][2][-40:] == RELAY else ("ur" if l["topics"][2][-40:] == UR else l["topics"][2][-40:][:8])
            side = "BUY " if a0 < 0 else "SELL"
            print(f"  blk +{bn-b0:4d} (buy{bn-bb:+3d}) idx {idx:2d} {side} {abs(a0)/1e18:.5f} ETH  via {who:6s} from {frm} nonce {nonce} gp {int(t.get('maxFeePerGas') or t['gasPrice'],16)/1e9:.4f} tip {int(t.get('maxPriorityFeePerGas') or '0x0',16)/1e9:.4f}")
        else:
            dl = sgn(W(d, 2)); print(f"  blk +{bn-b0:4d} (buy{bn-bb:+3d}) idx {idx:2d} {'ADD ' if dl > 0 else 'PULL'} liq {dl:.3e} from {frm} nonce {nonce} sel {t['input'][:10]} gp {int(t.get('maxFeePerGas') or t['gasPrice'],16)/1e9:.4f}")
