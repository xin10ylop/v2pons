# Who is 0x8cf143dd, the wallet that buys ahead of the bot in v3.0 pools from Oct 11 01:57 UTC: its txs in the fresh v3.0 pools (to, selector,
# value, gas price, calldata length, nonce), its sells, its current nonce and balance; and the same for the v2.433 decoys of Oct 10 for comparison.
import sys, json, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, batch, W, sgn, T_SWAP
D = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/report/work/fresh2"
pools = json.load(open(D + "/pools.json")); ev = json.load(open(D + "/events.json")); txs = json.load(open(D + "/txs.json"))
def s128(x): x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
rows = []; wallets = collections.Counter()
for p in pools:
    if p["sub"] != "v3.0": continue
    for x in sorted(ev[p["pid"]]["logs"], key=lambda x: (x["bn"], x["li"])):
        if x["t"] != T_SWAP: continue
        t = txs.get(x["tx"])
        if not t or not t["from"].startswith("0x8cf143dd"): continue
        a0 = s128(W(x["data"], 0))
        rows.append({"pid": p["pid"][:10], "off": x["bn"] - p["b0"], "side": "B" if a0 < 0 else "S", "eth": abs(a0) / 1e18, "from": t["from"], "to": t["to"], "sel": t["input"][2:10],
                     "len": (len(t["input"]) - 2) // 2, "value": t["value"] / 1e18, "nonce": t["nonce"], "ti": t["ti"]})
        wallets[t["from"]] += 1
print("wallets", wallets)
print("n rows", len(rows), "to/sel/len", collections.Counter((r["to"], r["sel"], r["len"]) for r in rows).most_common(5))
print("nonce range", min(r["nonce"] for r in rows), max(r["nonce"] for r in rows))
for r in rows[:12]: print(r)
w = list(wallets)[0]
print("now nonce", int(rpc("eth_getTransactionCount", [w, "latest"]), 16), "balance", int(rpc("eth_getBalance", [w, "latest"]), 16) / 1e18)
# a full tx for gas fields
h = None
for p in pools:
    for x in ev[p["pid"]]["logs"]:
        t = txs.get(x["tx"])
        if t and t["from"] == w: h = x["tx"]; break
    if h: break
t = rpc("eth_getTransactionByHash", [h]); print({k: t[k] for k in ("from", "to", "value", "gas", "gasPrice", "maxFeePerGas", "maxPriorityFeePerGas", "nonce", "type") if k in t}); print(t["input"][:10 + 64 * 10])
json.dump(rows, open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/report/work/decoy3.json", "w"), indent=0)
