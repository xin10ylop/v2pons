"""Find PM1444 v3.0 launches after the census window (Initialize logs, ETH as currency0, fee 10000, ts 200, no hook; launch tx to the
PositionManager, selector ac9650d8, 1444-byte calldata, 3.0 ETH). Writes new_v3.json."""
import sys, json, time
sys.path.insert(0, '..')
from chain import *
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
start = int(sys.argv[1]) if len(sys.argv) > 1 else 84238620
head = int(rpc('eth_blockNumber', []), 16)
out = []
inits = []
step = 20000
for a in range(start, head + 1, step):
    b = min(head, a + step - 1)
    ls = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, a, b)
    inits += ls
    print(a, b, len(ls), file=sys.stderr)
cand = []
for l in inits:
    d = l["data"]; fee = W(d, 0); ts = sgn(W(d, 1)); hooks = d[2 + 64*2 + 24: 2 + 64*3]
    if fee == 10000 and ts == 200 and hooks == "0" * 40: cand.append(l)
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in cand])
for l, t in zip(cand, txs):
    inlen = len(t["input"]) // 2 - 1; v = int(t["value"], 16) / 1e18
    rec = {"pid": l["topics"][1], "b0": int(l["blockNumber"], 16), "tx": l["transactionHash"], "token": "0x" + l["topics"][3][-40:], "to": t["to"], "sel": t["input"][:10],
           "inlen": inlen, "value": v, "from": t["from"], "nonce": int(t["nonce"], 16)}
    if (t["to"] or "").lower() == POSM and t["input"][:10] == "0xac9650d8" and inlen == 1444 and round(v, 3) == 3.0:
        out.append(rec)
    else:
        print("other fee1% ts200:", json.dumps(rec), file=sys.stderr)
json.dump({"head": head, "start": start, "pools": out}, open("new_v3.json", "w"), indent=1)
print("head", head, "inits", len(inits), "fee1%/ts200", len(cand), "v3.0", len(out))
if out: print("first", out[0]["b0"], "last", out[-1]["b0"])
