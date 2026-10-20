import json, sys
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
from chain import *
D = json.load(open("oct8.json")); pools = D["pools"]; ev = D["ev"]
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
OFF = 4 + 32 * 24
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
mine = sorted([pid for pid, ls in ev.items() if any(l["topics"][0] == T_SWAP and l["topics"][2][-40:] == RELAY for l in ls)], key=lambda p: pools[p]["bn"])
for n, pid in enumerate(mine, 1):
    p = pools[pid]; tok = p["token"]
    ls = sorted(ev[pid], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    B = [int(l["blockNumber"], 16) for l in ls if l["topics"][0] == T_SWAP and l["topics"][2][-40:] == RELAY][0]
    pull = min(int(l["blockNumber"], 16) for l in ls if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0)
    blks = batch([("eth_getBlockByNumber", [hex(b), True]) for b in range(p["bn"], pull + 3)])
    txs = [t for b in blks for t in b["transactions"] if tok in t["input"].lower() and t["to"] and t["to"][2:].lower() == UR]
    recs = batch([("eth_getTransactionReceipt", [t["hash"]]) for t in txs])
    print(f"\n== T{n} buy blk {B}, pull +{pull-B}")
    for t, r in zip(txs, recs):
        d = bytes.fromhex(t["input"][2:]); amt = int.from_bytes(d[OFF:OFF+32], "big"); mn = int.from_bytes(d[OFF+32:OFF+64], "big"); z41 = int.from_bytes(d[OFF-32:OFF], "big")
        dl = int.from_bytes(d[4+64:4+96], "big")
        out = None
        for l in r["logs"]:
            if l["topics"] and l["topics"][0] == T_SWAP: out = s128(W(l["data"], 1))
        print(f"  +{int(r['blockNumber'],16)-B:4d} idx {int(r['transactionIndex'],16):2d} {t['from'][2:10]} nonce {int(t['nonce'],16):3d} value {int(t['value'],16)/1e18:.5f} zeroForOne {z41} amountIn {amt/1e18:.5f} minOut {mn:.4e} got {out if out is None else f'{out:.4e}'} status {r['status']} gasUsed {int(r['gasUsed'],16)} deadline {'max' if dl == (1<<256)-1 else dl}")
