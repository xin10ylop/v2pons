"""Every v4 pool initialised in the last N minutes, grouped by launcher / value / fee / tick spacing (public RPC, read-only)."""
import sys, time, json, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, logs, batch, PM, T_INIT, W
minutes = float(sys.argv[1]) if len(sys.argv) > 1 else 60
head = int(rpc("eth_blockNumber", []), 16)
hb = rpc("eth_getBlockByNumber", [hex(head), False]); t_head = int(hb["timestamp"], 16)
lo = head - 1000; tb = int(rpc("eth_getBlockByNumber", [hex(lo), False])["timestamp"], 16); bps = 1000 / max(1, t_head - tb)
start = head - int(minutes * 60 * bps)
print(f"head {head} ({time.strftime('%H:%M:%S', time.gmtime(t_head))} UTC), {bps:.1f} blocks/s, scanning {start}..{head}")
ls = []
step = 2000
for a in range(start, head + 1, step):
    ls += logs({"address": PM, "topics": [T_INIT]}, a, min(a + step - 1, head))
print(len(ls), "Initialize logs")
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in ls])
blocks = {}
for bn in sorted({int(l["blockNumber"], 16) for l in ls})[::max(1, len(ls) // 20)]:
    blocks[bn] = int(rpc("eth_getBlockByNumber", [hex(bn), False])["timestamp"], 16)
groups = collections.defaultdict(list)
for l, tx in zip(ls, txs):
    if not tx: continue
    d = l["data"]; fee = W(d, 2); ts = W(d, 3); c0 = l["topics"][2][-40:]; c1 = l["topics"][3][-40:]
    val = int(tx["value"], 16) / 1e18; to = (tx.get("to") or "create")[-8:]; clen = (len(tx["input"]) - 2) // 2
    key = (to, clen, round(val, 7), fee, ts, "ETH" if c0 == "0" * 40 else c0[:6])
    groups[key].append((int(l["blockNumber"], 16), tx["from"][-8:]))
rows = sorted(groups.items(), key=lambda kv: -len(kv[1]))
print(f"{'to':>8} {'clen':>5} {'value':>11} {'fee':>7} {'ts':>5} quote   n  wallets  first..last block")
for k, v in rows[:25]:
    print(f"{k[0]:>8} {k[1]:>5} {k[2]:>11} {k[3]:>7} {k[4]:>5} {k[5]:<6} {len(v):>3}  {len({w for _, w in v}):>5}   {min(b for b, _ in v)}..{max(b for b, _ in v)}")
# the volume bot's PositionManager launches by 10-minute bucket and shape
posm = [(k, b) for k, v in groups.items() for b, _ in v if k[0] == "e8a04fa7"]
tsmap = sorted(blocks.items())
def t_of(bn):
    for b, t in tsmap:
        if b >= bn: return t
    return t_head
buck = collections.defaultdict(collections.Counter)
for k, b in posm:
    buck[int(t_of(b) // 600) * 600][(k[1], k[2], k[3], k[4])] += 1
print("\nPositionManager launches per 10 min by (calldata len, value, fee, ts):")
for t in sorted(buck):
    print(" ", time.strftime("%H:%M", time.gmtime(t)), dict(buck[t].most_common(6)))
