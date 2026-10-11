# Did the volume bot's router 0x1cbaf24d buy into any ETH pool launched after the census OTHER than v3.0/v5.0 (a re-fingerprinted v2.433)?
# Every ETH-pair Initialize from the census head to the chain head; for every pool, its Swap logs in launch..launch+40; the tx of every buy of
# 0.004 ETH or more in that span; count pools whose such buy was sent to the router (selector c1120e3d), by fingerprint. Output router_scan.json.
import sys, json, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, W, sgn
OUT = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/report/work/router_scan.json"
ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
a = 85203898; head = int(rpc("eth_blockNumber", []), 16) - 50
L = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, head)
pools = []
for l in L:
    d = l["data"]; pools.append({"pid": l["topics"][1], "bn": int(l["blockNumber"], 16), "fp": (W(d, 0), sgn(W(d, 1)), d[2 + 64 * 2 + 24: 2 + 64 * 3] == "0" * 40, str(W(d, 3)))})
print("pools", len(pools))
cand = []
for i in range(0, len(pools), 40):
    g = pools[i:i + 40]; lo = min(p["bn"] for p in g); hi = min(head, max(p["bn"] for p in g) + 40)
    by = {p["pid"]: p for p in g}
    for s in logs({"address": PM, "topics": [T_SWAP, [p["pid"] for p in g]]}, lo, hi):
        p = by[s["topics"][1]]; bn = int(s["blockNumber"], 16)
        if bn > p["bn"] + 40: continue
        a0 = sgn(W(s["data"], 0)); a0 = a0 - (1 << 128) if a0 >= (1 << 127) else a0
        if a0 <= -int(0.004e18): cand.append((p, bn - p["bn"], -a0 / 1e18, s["transactionHash"]))
print("buys >= 0.004 ETH within +40:", len(cand))
hs = sorted({c[3] for c in cand}); tx = {}
for i in range(0, len(hs), 50):
    for h, t in zip(hs[i:i + 50], batch([("eth_getTransactionByHash", [h]) for h in hs[i:i + 50]])):
        if t: tx[h] = (t["to"], t["input"][2:10])
hit = collections.Counter(); ex = {}
for p, off, eth, h in cand:
    if tx.get(h, (None, None))[0] == ROUTER:
        k = str(p["fp"]); hit[k] += 1; ex.setdefault(k, (p["pid"], off, eth))
res = {"from": a, "head": head, "pools": len(pools), "big_buys": len(cand), "router_buy_pools_by_fingerprint": dict(hit), "examples": ex}
json.dump(res, open(OUT, "w"), indent=1); print(json.dumps(res, indent=1))
