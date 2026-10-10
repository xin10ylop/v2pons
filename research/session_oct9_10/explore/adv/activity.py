"""Family launches per hour from the census start to the chain head (census pools.pkl + Initialize logs after the census window)."""
import sys, os, json, pickle, collections, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad"); sys.path.insert(0, ".")
from chain import rpc, batch, logs, PM, T_INIT, W, sgn
from fams import hours, T0
PM_POS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
P = pickle.load(open("pools.pkl", "rb"))
inw = [p["b0"] for p in P.values() if p.get("to") == PM_POS and p.get("inlen") == 1444 and p.get("fee") == 2500 and p.get("ts") == 50 and abs((p.get("value") or 0) - 2.4333285) < 1e-9]
head = int(rpc("eth_blockNumber", []), 16); tsh = int(rpc("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
START = 84238620
L = []; a = START
while a <= head:
    b = min(a + 49999, head); L += logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, b); a = b + 1
hs = sorted({l["transactionHash"] for l in L}); tx = {}
cache = "adv/activity_tx.pkl"
if os.path.exists(cache): tx = pickle.load(open(cache, "rb"))
need = [h for h in hs if h not in tx]
for i in range(0, len(need), 50):
    for h, t in zip(need[i:i + 50], batch([("eth_getTransactionByHash", [h]) for h in need[i:i + 50]])):
        if t: tx[h] = {"to": (t["to"] or "").lower(), "inlen": (len(t["input"]) - 2) // 2, "value": int(t["value"], 16), "from": t["from"].lower(), "nonce": int(t["nonce"], 16), "sel": t["input"][:10]}
    time.sleep(0.2)
pickle.dump(tx, open(cache, "wb"))
after = []; near = collections.Counter()
for l in L:
    d = l["data"]; t = tx.get(l["transactionHash"])
    if not t: continue
    fee = W(d, 0); ts = sgn(W(d, 1)); hooks = d[2 + 64 * 2 + 24: 2 + 64 * 3]
    full = t["to"] == PM_POS and t["inlen"] == 1444 and fee == 2500 and ts == 50 and t["value"] == 2433328500000000000 and hooks == "0" * 40
    if full: after.append((int(l["blockNumber"], 16), t["nonce"], l["topics"][1], l["transactionHash"], t["from"], "0x" + l["topics"][3][-40:]))
    elif t["to"] == PM_POS and t["inlen"] == 1444:
        near[(fee, ts, t["value"] / 1e18, hooks == "0" * 40)] += 1
print("head", head, "time", time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(tsh)), "UTC; family launches after the census window:", len(after))
print("PM1444 launches after the window with other fields (fee, ts, value, hooks0):", near.most_common(8))
# exact wei value in-window
vals = collections.Counter(round(p["value"] * 1e18) for p in P.values() if p.get("to") == PM_POS and p.get("inlen") == 1444 and p.get("fee") == 2500)
print("in-window PM1444 fee2500 launch values (wei):", vals.most_common(4))
c = collections.Counter()
for b in inw: c[int(hours(b))] += 1
for b, *_ in after: c[int(hours(b))] += 1
hh = sorted(c)
print("launches per hour (h from Oct 8 00:00 UTC):", " ".join(f"{h}:{c[h]}" for h in range(hh[0], hh[-1] + 1)))
json.dump({"head": head, "head_ts": tsh, "after": after, "per_hour": c}, open("adv/activity.json", "w"))
