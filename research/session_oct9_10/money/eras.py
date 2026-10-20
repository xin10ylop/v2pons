"""sample launches across the launcher's history: funding before (sweep/dispatcher signature?) and payout after the pull"""
import json, collections, sys
from tr import *
d = json.load(open("../ops/launcher_txs.json"))
V = sorted(((h, v) for h, v in d.items()), key=lambda x: x[1]["bn"])
def pick(cond, k):
    c = [x for x in V if cond(x[1])]
    return [c[int(i * (len(c) - 1) / max(1, k - 1))] for i in range(k)] if c else []
samples = []
samples += [("era 1.97 ETH", x) for x in pick(lambda v: abs(v["value"] / 1e18 - 1.97) < 0.005 and v["nonce"] == 0, 2)]
samples += [("era 0.45 ETH", x) for x in pick(lambda v: abs(v["value"] / 1e18 - 0.45) < 0.005 and v["nonce"] == 0, 1)]
samples += [("early", x) for x in pick(lambda v: v["bn"] < 25843503 and v["nonce"] == 0, 1)]
samples += [("repeat sender 0xef441005", x) for x in pick(lambda v: v["from"] == "0xef44100548a252403dba9c7b9ee5257f87936c92", 1)]
for tag, (h, v) in samples:
    rec = rpc("eth_getTransactionReceipt", [h]); bn = v["bn"]; dep = v["from"]
    pid = next((l["topics"][1] for l in rec["logs"] if l["topics"][0] == T_INIT), None)
    pulls = []
    if pid:
        for a in range(bn, bn + 400000, 99999):
            pulls = [int(x["blockNumber"], 16) for x in logs({"address": PM, "topics": [T_ML, pid]}, a, a + 99998) if sgn(W(x["data"], 2)) < 0]
            if pulls: break
    print(f"\n== {tag}: launch blk {bn} sender {dep} (nonce {v['nonce']}) value {v['value']/1e18:.3f} ETH pid {str(pid)[:12]} first pull {pulls[0] if pulls else None}", flush=True)
    for n, t in touching([dep], bn - 400, bn):
        if t[2] == dep: print("   funded:", show(n, t, bn), flush=True)
    if pulls:
        P = pulls[0]; outs = [(n, t) for n, t in touching([dep], P, P + 500) if t[1] == dep]
        for n, t in outs: print("   after pull:", show(n, t, P), flush=True)
        pay = next(((n, t) for n, t in outs if t[3] > 10**16), None)
        if pay:
            s = pay[1][2]; ins = [(n, t) for n, t in touching([s], pay[0] - 10, pay[0] + 60)]
            print(f"   payout went to {s[:12]}: {sum(1 for n, t in ins if t[2] == s)} transfers in around it; its outs: " + "; ".join(show(n, t, pay[0]) for n, t in ins if t[1] == s), flush=True)
    save()
