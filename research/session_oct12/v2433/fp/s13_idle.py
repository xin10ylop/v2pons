"""Are the 2.4333 line's wallets idle since it stopped? For each 2.4333 buyer wallet (router -> wallet recipients, s06): the nonce at its last
2.4333 bot buy (that transaction's nonce) against its nonce and balance now; for the launcher wallets: nonce and balance now."""
import json, collections, time
from clusters import load
from common import R, load_jsonl
rows = load(); vb = {r["c1"]: r for r in rows if r["fam"].startswith("VB 2.4333")}
last = {}
for x in load_jsonl("s06_bot_transfers_cache.jsonl"):
    if x["side"] == "from" and x["token"] in vb:
        w = "0x" + x["t2"][-40:]
        if w not in last or x["b"] > last[w][0]: last[w] = (x["b"], x["h"])
ws = sorted(last)
txs = R.batch("eth_getTransactionByHash", [[last[w][1]] for w in ws])
now_n = R.batch("eth_getTransactionCount", [[w, "latest"] for w in ws]); now_b = R.batch("eth_getBalance", [[w, "latest"] for w in ws])
c = collections.Counter(); out = []
for w, tx, n, b in zip(ws, txs, now_n, now_b):
    if tx["from"].lower() != w: c["recipient is not the tx sender"] += 1; continue
    d = int(n, 16) - int(tx["nonce"], 16) - 1
    out.append((d, int(b, 16) / 1e18, w, last[w][0]))
ds = sorted(o[0] for o in out)
print("2.4333 buyer wallets:", len(ws), dict(c), "| txs sent since their last 2.4333 bot buy: p10/50/90/max", ds[len(ds)//10], ds[len(ds)//2], ds[9*len(ds)//10], ds[-1],
      "| zero:", sum(d == 0 for d in ds), "| balance ETH p50/max %.4f/%.4f, total %.3f" % (sorted(o[1] for o in out)[len(out)//2], max(o[1] for o in out), sum(o[1] for o in out)))
print("  last 2.4333 bot buy block of these wallets: max", max(o[3] for o in out))
L = [r for r in rows if r["fam"].startswith("VB 2.4333")]
n2 = R.batch("eth_getTransactionCount", [[r["from"], "latest"] for r in L]); b2 = R.batch("eth_getBalance", [[r["from"], "latest"] for r in L])
cn = collections.Counter(int(n, 16) for n in n2)
print("2.4333 launcher wallets:", len(L), "nonce now:", dict(sorted(cn.items())), "| balance ETH now p50/max %.5f/%.5f total %.4f" % (sorted(int(b, 16) / 1e18 for b in b2)[len(L)//2], max(int(b, 16) / 1e18 for b in b2), sum(int(b, 16) / 1e18 for b in b2)))
for r, n, b in list(zip(L, n2, b2))[-6:]: print("   ", time.strftime("%H:%M:%S", time.gmtime(r["t"])), r["from"], "nonce at launch", r["nonce"], "now", int(n, 16), "balance %.6f" % (int(b, 16) / 1e18))
