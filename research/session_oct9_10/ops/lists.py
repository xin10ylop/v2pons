"""All bonding-curve 'listing' events (topic 0xe4b7e48f..., topic1 = an address) naming any A or B crowd wallet, Oct 7 -> head; per curve: which A/B wallets, creator."""
import sys, json, time, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops")
from lib import *
rc = rpc("eth_getTransactionReceipt", ["0x" + "c0e9c3651fec32"[2:]]) if False else None
# full topic from the f3d9 creation tx
tx = [t for t in rpc("eth_getBlockByNumber", [hex(83085579), True])["transactions"] if t["from"].lower() == "0xf3d9f9fd787098ddedd6d3dd1c5ef8231b0a8a72"][0]
rc = rpc("eth_getTransactionReceipt", [tx["hash"]])
TL = next(l["topics"][0] for l in rc["logs"] if l["topics"][0].startswith("0xe4b7e48f"))
print("TL", TL)
b = json.load(open(D + "b_list.json")); A = set(b["A"]); B = set(b["B"])
TW = ["0x" + "0" * 24 + w[2:] for w in sorted(A | B)]
head = int(rpc("eth_blockNumber", []), 16); START = 82000000
calls = [("eth_getLogs", [{"topics": [TL, TW], "fromBlock": hex(s), "toBlock": hex(min(s + 29999, head))}]) for s in range(START, head + 1, 30000)]
out = []
for i in range(0, len(calls), 10):
    for k in range(10):
        try:
            r = post([{"jsonrpc": "2.0", "id": j, "method": m, "params": p} for j, (m, p) in enumerate(calls[i:i + 10])])
            if isinstance(r, list) and all("result" in x for x in r): break
        except RuntimeError: pass
        time.sleep(2 + 2 * k)
    else: raise RuntimeError("logs")
    for x in r: out += x["result"]
print("listing logs naming A/B", len(out))
cur = collections.defaultdict(lambda: {"A": set(), "B": set(), "tx": set(), "bn": None})
for l in out:
    w = "0x" + l["topics"][1][-40:]; c = cur[l["address"].lower()]
    c["A" if w in A else "B"].add(w); c["tx"].add(l["transactionHash"]); c["bn"] = int(l["blockNumber"], 16)
fac = json.load(open(D + "bcurve_factory.json"))["logs"]
by_curve = {"0x" + l["topics"][2][-40:]: l for l in fac}
res = {}
for a, c in sorted(cur.items(), key=lambda kv: kv[1]["bn"]):
    f = by_curve.get(a); creator = "0x" + f["data"][26:66] if f else None; token = "0x" + f["topics"][1][-40:] if f else None
    res[a] = {"bn": c["bn"], "nA": len(c["A"]), "nB": len(c["B"]), "creator": creator, "token": token, "txs": sorted(c["tx"])}
    print(a, c["bn"], "A", len(c["A"]), "B", len(c["B"]), "creator", creator, "token", token, "ntx", len(c["tx"]))
json.dump(res, open(D + "lists.json", "w"), indent=1)
