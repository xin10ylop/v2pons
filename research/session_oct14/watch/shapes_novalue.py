"""v4 launches of the last N hours grouped by shape WITHOUT the ETH value (target, calldata length, fee, tick spacing, quote, hook),
so a family whose launch amount varies per launch is not split into tiny groups (public RPC, read-only)."""
import sys, collections, statistics
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, logs, batch, PM, T_INIT, W
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 6
head = int(rpc("eth_blockNumber", []), 16); start = head - int(hours * 3600 * 9.8)
ls = []
for a in range(start, head + 1, 2000):
    ls += logs({"address": PM, "topics": [T_INIT]}, a, min(a + 1999, head))
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in ls])
g = collections.defaultdict(list)
for l, t in zip(ls, txs):
    if not t: continue
    d = l["data"]; hook = "%040x" % W(d, 2); c0 = l["topics"][2][-40:]
    key = ((t.get("to") or "create")[-8:], (len(t["input"]) - 2) // 2, W(d, 0), W(d, 1), "ETH" if c0 == "0" * 40 else c0[:6], "-" if hook == "0" * 40 else hook[-8:])
    g[key].append((int(t["value"], 16) / 1e18, t["from"], int(l["blockNumber"], 16), W(d, 3)))
print(f"head {head}: {len(ls)} Initialize logs in {hours:.0f} h; shapes without the ETH value, >= 8 launches:")
print(f"{'to':>8} {'clen':>5} {'fee':>8} {'ts':>4} quote  hook        n wallets values  value min/med/max        prices")
for k, v in sorted(g.items(), key=lambda kv: -len(kv[1])):
    if len(v) < 8: continue
    vals = [x[0] for x in v]
    print(f"{k[0]:>8} {k[1]:>5} {k[2]:>8} {k[3]:>4} {k[4]:<6} {k[5]:<8} {len(v):>4} {len({x[1] for x in v}):>7} {len({round(x, 7) for x in vals}):>6}  "
          f"{min(vals):.4f}/{statistics.median(vals):.4f}/{max(vals):.4f}  {len({x[3] for x in v}):>6}")
