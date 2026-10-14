"""Robinhood Chain: every v4 Initialize from Oct 13 21:00 UTC to the head with fee 5000/ts 100, the 2.433/3.0/5.0 prices, or a native pair whose
launch value ends in .4333285 (light check that the line did not return home)."""
import sys, json, collections, time; sys.path.insert(0, '.'); import rpcx
from eth_utils import keccak
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; Z = "0x" + "0" * 40
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
h, th = rpcx.head("rh"); a = h - int((th - 1791932400) / 0.1)   # Oct 13 21:00 UTC
while rpcx.ts_of("rh", a) > 1791932400: a -= 20000
rows = []
for s in range(a, h + 1, 100000):
    for l in rpcx.logs("rh", {"address": PM, "topics": [T_INIT]}, s, min(s + 99999, h)):
        d = l["data"][2:]; w = [int(d[i:i + 64], 16) for i in range(0, len(d), 64)]
        rows.append({"b": int(l["blockNumber"], 16), "tx": l["transactionHash"], "c0": "0x" + l["topics"][2][-40:], "c1": "0x" + l["topics"][3][-40:], "fee": w[0], "ts": w[1], "hooks": w[2], "sqrtP": w[3]})
print("RH Initialize since Oct 13 21:00:", len(rows), "blocks", a, h)
S = {1604517591721945638372359205383840: "2433", 679394651928963067279918579724198: "3.0", 526364174002223567019744861584709: "5.0"}
print("by known price:", collections.Counter(S.get(r["sqrtP"], "other") for r in rows))
print("fee 5000/ts 100 or 2500/50:", [(r["b"], r["c1"]) for r in rows if (r["fee"], r["ts"]) in ((5000, 100), (2500, 50))])
nat = [r for r in rows if r["c0"] == Z and r["hooks"] == 0 and S.get(r["sqrtP"]) is None]
txs = rpcx.batch("rh", "eth_getTransactionByHash", [[r["tx"]] for r in nat], n=20) if nat else []
v = collections.Counter(round(int(t["value"], 16) / 1e18, 7) for t in txs if t)
print("native no-hook launches with other prices:", len(nat), "values ending .4333285:", {k: c for k, c in v.items() if abs((k % 1) - 0.4333285) < 1e-9})
json.dump(rows, open("c23_rh_recent.json", "w"))
