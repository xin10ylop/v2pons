"""Do the candidate families keep launching after the census window? Initialize logs (currency0 = ETH) from the window end to the head,
their launch txs; counts per family and per hour. -> after.json"""
import sys, os, json, collections, time
sys.path.insert(0, "..")
from chain import rpc, batch, logs, PM, T_INIT, W, sgn
START = 84238620
head = int(rpc("eth_blockNumber", []), 16)
L = []
a = START
while a <= head:
    b = min(a + 99999, head); L += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, b); a = b + 1
print("pools after window", len(L), "blocks", head - START, flush=True)
hs = sorted({l["transactionHash"] for l in L})
tx = {}
for i in range(0, len(hs), 50):
    for h, t in zip(hs[i:i + 50], batch([("eth_getTransactionByHash", [h]) for h in hs[i:i + 50]])):
        if t: tx[h] = {"to": (t["to"] or "").lower(), "sel": t["input"][:10], "inlen": (len(t["input"]) - 2) // 2, "value": int(t["value"], 16) / 1e18, "nonce": int(t["nonce"], 16)}
    time.sleep(0.3)
c = collections.Counter(); rows = []
for l in L:
    d = l["data"]; fee = W(d, 0); ts = sgn(W(d, 1)); hooks = d[2 + 64 * 2 + 24: 2 + 64 * 3]; t = tx.get(l["transactionHash"], {})
    k = None
    if hooks == "0" * 40 and t:
        if t["to"] == "0x58daec3116aae6d93017baaea7749052e8a04fa7" and t["inlen"] == 1444 and fee == 2500 and ts == 50 and abs(t["value"] - 2.4333285) < 1e-9: k = "v2.433"
        elif t["to"] == "0x58daec3116aae6d93017baaea7749052e8a04fa7" and t["inlen"] == 1444 and fee == 10000 and ts == 200 and t["value"] == 5.0: k = "v5.0"
        elif t["to"] == "0x58daec3116aae6d93017baaea7749052e8a04fa7" and t["inlen"] == 1444 and fee == 10000 and ts == 200 and t["value"] == 3.0: k = "v3.0"
        elif t["to"] == "0x8366a39cc670b4001a1121b8f6a443a643e40951" and t["sel"] == "0x6276cbbe" and fee == 500 and ts == 1: k = "PMdirect0.05%"
        elif t["to"] == "0x3194e32622c5d860a0572c74edda99dcfd8fc827": k = "OURS-orig"
        elif t["to"] == "0x58daec3116aae6d93017baaea7749052e8a04fa7" and t["inlen"] == 2276: k = "PM2276"
    c[k or "other"] += 1; rows.append({"b0": int(l["blockNumber"], 16), "fam": k, "nonce": t.get("nonce")})
hours = (head - START) * 0.1027 / 3600
print("head", head, "hours after window ~", round(hours, 2))
for k, v in c.most_common(): print(f"  {k:16s} {v:4d}  per day ~{v / hours * 24:.0f}")
json.dump({"head": head, "hours": hours, "counts": c, "rows": rows}, open("after.json", "w"))
