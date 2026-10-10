import json, sys, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
D = json.load(open("../oct8.json")); pools = D["pools"]; ev = D["ev"]
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"; WAL = "ab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
hashes = sorted({l["transactionHash"] for ls in ev.values() for l in ls})
T = dict(zip(hashes, batch([("eth_getTransactionByHash", [h]) for h in hashes])))
def ours(l): return l["topics"][2][-40:] == RELAY or T[l["transactionHash"]]["from"][2:].lower() == WAL
mine = sorted([pid for pid, ls in ev.items() if any(l["topics"][0] == T_SWAP and ours(l) for l in ls)], key=lambda p: pools[p]["bn"])
print("trades", len(mine))
need = {}
rows = []
for k, pid in enumerate(mine, 1):
    p = pools[pid]; b0 = p["bn"]; ls = sorted(ev[pid], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    ob = [l for l in ls if l["topics"][0] == T_SWAP and ours(l)]; bb = int(ob[0]["blockNumber"], 16)
    items = [("launch", b0, None)]
    trig = None
    for l in ls:
        bn = int(l["blockNumber"], 16)
        if bn > bb + 20: break
        if l["topics"][0] == T_SWAP:
            a0 = sgn(W(l["data"], 0)); a0 = a0 - (1 << 128) if a0 >= (1 << 127) else a0
            if ours(l): items.append(("OUR " + ("buy" if a0 < 0 else "sell"), bn, l["transactionHash"]))
            elif a0 < 0 and -a0 >= 2e14:
                if trig is None and bn <= bb: trig = bn; items.append(("trigger", bn, l["transactionHash"]))
                elif bn >= bb: items.append(("crowd buy", bn, l["transactionHash"]))
        else:
            if sgn(W(l["data"], 2)) < 0: items.append(("PULL", bn, l["transactionHash"]))
    rows.append((k, bb, items))
    for _, bn, _ in items: need[bn] = None
bl = sorted(need); res = batch([("eth_getBlockByNumber", [hex(b), False]) for b in bl])
ntx = {b: len(r["transactions"]) for b, r in zip(bl, res)}
for k, bb, items in rows:
    print(f"trade {k}: our buy block {bb}")
    for name, bn, h in items:
        flag = "  <-- ALONE in its block: kind-4 feed msg, engine blind" if ntx[bn] == 2 else ""
        print(f"   {name:10s} blk {bn} (buy{bn-bb:+d}) user txs in block {ntx[bn]-1}{flag}")
