"""Pools initialised by a direct PoolManager.initialize call (196-B calldata to the PoolManager itself) in the last N minutes:
liquidity and swaps from the launch to +600 blocks, and who sends them (public RPC, read-only)."""
import sys, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, logs, batch, PM, T_INIT, T_SWAP, T_ML, W, sgn
minutes = float(sys.argv[1]) if len(sys.argv) > 1 else 180
head = int(rpc("eth_blockNumber", []), 16); start = head - int(minutes * 60 * 9.8)
ls = []
for a in range(start, head + 1, 2000):
    ls += logs({"address": PM, "topics": [T_INIT]}, a, min(a + 1999, head))
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in ls])
mine = [(l, t) for l, t in zip(ls, txs) if t and (t.get("to") or "").lower() == PM and (len(t["input"]) - 2) // 2 == 196]
print(f"head {head}: {len(mine)} direct PoolManager.initialize launches in {minutes:.0f} min (of {len(ls)})")
pids = {l["topics"][1]: (int(l["blockNumber"], 16), t["from"], W(l["data"], 0), W(l["data"], 1)) for l, t in mine}
ev = collections.defaultdict(list)
for a in range(min(b for b, *_ in pids.values()), head + 1, 2000):
    for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], list(pids)]}, a, min(a + 1999, head)):
        ev[l["topics"][1]].append(l)
alltx = sorted({l["transactionHash"] for v in ev.values() for l in v})
tx = dict(zip(alltx, batch([("eth_getTransactionByHash", [h]) for h in alltx])))
senders = collections.Counter(); pools_with_swaps = 0; liq = 0
for pid, (b0, launcher, fee, ts) in sorted(pids.items(), key=lambda kv: kv[1][0]):
    rows = sorted(ev[pid], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    sw = [l for l in rows if l["topics"][0] == T_SWAP and int(l["blockNumber"], 16) <= b0 + 600]
    ml = [l for l in rows if l["topics"][0] == T_ML]
    liq += bool(ml); pools_with_swaps += bool(sw)
    for l in sw: senders[(tx[l["transactionHash"]]["from"][:10], (tx[l["transactionHash"]].get("to") or "")[:10])] += 1
    eth_in = sum(max(0, -sgn(W(l["data"], 0))) for l in sw) / 1e18
    print(f"  {b0} launcher {launcher[:10]} fee {fee} ts {ts}: liquidity events {len(ml)}, swaps to +600 {len(sw)}, ETH in {eth_in:.4f}",
          "first swap +%d" % (int(sw[0]['blockNumber'], 16) - b0) if sw else "")
print(f"pools with liquidity added: {liq}; with a swap by +600: {pools_with_swaps}")
print("swap senders (from, to) seen in more than one swap:", [(k, n) for k, n in senders.most_common(8) if n > 1])
