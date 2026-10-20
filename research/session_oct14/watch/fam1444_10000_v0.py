"""The 1,444-byte PositionManager launches at fee 10000 / tick spacing 200 at a value other than 3 or 5 ETH with ETH (seen Oct 14 in the 48 h no-value grouping): launches,
values, prices, launcher nonces, and every swap from the launch to +400 with its sender and router (read-only)."""
import sys, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, logs, batch, PM, T_INIT, T_SWAP, T_ML, W, sgn
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 48
head = int(rpc("eth_blockNumber", []), 16); start = head - int(hours * 3600 * 9.8)
ls = []
for a in range(start, head + 1, 20000):
    ls += logs({"address": PM, "topics": [T_INIT]}, a, min(a + 19999, head))
ls = [l for l in ls if W(l["data"], 0) == 10000 and W(l["data"], 1) == 200 and l["topics"][2][-40:] == "0" * 40]
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in ls])
fam = [(l, t) for l, t in zip(ls, txs) if t and (t.get("to") or "").lower() == POSM and (len(t["input"]) - 2) // 2 == 1444 and int(t["value"], 16) not in (3 * 10**18, 5 * 10**18)]
print(f"head {head}: {len(fam)} launches (1,444 B, fee 10000, ts 200, ETH, value not 3 or 5) in {hours:.0f} h")
nonces = batch([("eth_getTransactionCount", [t["from"], hex(int(l["blockNumber"], 16))]) for l, t in fam])
pids = {}
for (l, t), n in zip(fam, nonces):
    b = int(l["blockNumber"], 16); pids[l["topics"][1]] = (b, t["from"], int(t["value"], 16) / 1e18, W(l["data"], 3), int(n, 16) if n else None, l["topics"][3][-40:])
ev = collections.defaultdict(list)
if pids:
    lo = min(v[0] for v in pids.values())
    for a in range(lo, head + 1, 20000):
        for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], list(pids)]}, a, min(a + 19999, head)): ev[l["topics"][1]].append(l)
hs = sorted({l["transactionHash"] for v in ev.values() for l in v})
tx = dict(zip(hs, batch([("eth_getTransactionByHash", [h]) for h in hs])))
routers = collections.Counter(); firsts = []
for pid, (b0, who, val, sp, n, tok) in sorted(pids.items(), key=lambda kv: kv[1][0]):
    rows = sorted(ev[pid], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    sw = [l for l in rows if l["topics"][0] == T_SWAP and int(l["blockNumber"], 16) <= b0 + 400]
    pulls = [int(l["blockNumber"], 16) - b0 for l in rows if l["topics"][0] == T_ML and sgn(W(l["data"], 2)) < 0]
    buys = []
    for l in sw:
        a0 = sgn(W(l["data"], 0)); t = tx[l["transactionHash"]]
        if a0 < 0: buys.append((int(l["blockNumber"], 16) - b0, -a0 / 1e18, t["from"][:10], (t.get("to") or "")[:10], t["input"][:10]))
        routers[((t.get("to") or "")[:10], t["input"][:10])] += 1
    big = [x for x in buys if x[1] >= 0.01]
    firsts.append(big[0][0] if big else None)
    print(f"  L {b0} val {val:.4f} launcher {who[:10]} nonce {n} token ..{tok[-6:]} swaps {len(sw)} buys {len(buys)} ETH in {sum(x[1] for x in buys):.3f}",
          "first >=0.01:", big[0] if big else None, "| pull at", pulls[:1])
print("swap (router, selector) counts:", routers.most_common(8))
f = sorted(x for x in firsts if x is not None); print("first buy >= 0.01 ETH offsets:", f)
