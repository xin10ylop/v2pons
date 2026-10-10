"""Forward data: candidate-family pools launched after the census window (b0 > 84238619) whose [b0, b0+3000] is complete;
their Swap + ModifyLiquidity logs (grouped getLogs, as others/fetch.py). -> fwd_pools.pkl in the pools.pkl format."""
import sys, os, json, pickle, time
sys.path.insert(0, "..")
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, T_ML, W, sgn
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
A = json.load(open("after.json")); head = A["head"]
START = 84238620; SPAN = 3000
L = logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, START, head - SPAN)
fam_by_b0 = {}
hs = sorted({l["transactionHash"] for l in L}); tx = {}
for i in range(0, len(hs), 50):
    for h, t in zip(hs[i:i + 50], batch([("eth_getTransactionByHash", [h]) for h in hs[i:i + 50]])):
        if t: tx[h] = t
    time.sleep(0.3)
pools = {}
for l in L:
    d = l["data"]; fee = W(d, 0); ts = sgn(W(d, 1)); hooks = "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3]; t = tx.get(l["transactionHash"])
    if hooks != "0x" + "0" * 40 or not t: continue
    to = (t["to"] or "").lower(); inlen = (len(t["input"]) - 2) // 2; v = int(t["value"], 16) / 1e18
    k = None
    if to == "0x58daec3116aae6d93017baaea7749052e8a04fa7" and inlen == 1444 and fee == 2500 and ts == 50 and abs(v - 2.4333285) < 1e-9: k = "L:0x58daec31|0xac9650d8|len1444|fee2500|ts50|v2.433"
    elif to == "0x58daec3116aae6d93017baaea7749052e8a04fa7" and inlen == 1444 and fee == 10000 and ts == 200 and v == 5.0: k = "L:0x58daec31|0xac9650d8|len1444|fee10000|ts200|v5.0"
    elif to == "0x8366a39cc670b4001a1121b8f6a443a643e40951" and t["input"][:10] == "0x6276cbbe" and fee == 500 and ts == 1: k = "L:0x8366a39c|0x6276cbbe|len196|fee500|ts1|v0"
    elif to == "0x3194e32622c5d860a0572c74edda99dcfd8fc827": k = "L:OURS-orig"
    elif to == "0x58daec3116aae6d93017baaea7749052e8a04fa7" and inlen == 2276 and fee == 100: k = "L:0x58daec31|0xac9650d8|len2276|fee100|ts1|v0"
    elif to == "0x58daec3116aae6d93017baaea7749052e8a04fa7" and inlen == 1444 and fee == 10000 and ts == 200 and v == 3.0: k = "L:0x58daec31|0xac9650d8|len1444|fee10000|ts200|v3.0"
    if not k: continue
    pid = l["topics"][1]
    pools[pid] = {"pid": pid, "b0": int(l["blockNumber"], 16), "tx": l["transactionHash"], "token": "0x" + l["topics"][3][-40:], "fee": fee, "ts": ts, "hooks": hooks,
                  "from": t["from"].lower(), "to": to, "nonce": int(t["nonce"], 16), "sel": t["input"][:10], "inlen": inlen, "value": v, "fam": k,
                  "sp0": W(d, 3), "tick0": sgn(W(d, 4)), "txindex": int(l["transactionIndex"], 16), "ours": "orig" if k == "L:OURS-orig" else None, "sw": [], "mls": []}
print("forward pools", len(pools), flush=True)
srt = sorted(pools.values(), key=lambda p: p["b0"]); groups = []; g = []
for p in srt:
    if g and (p["b0"] - g[0]["b0"] > 6000 or len(g) >= 40): groups.append(g); g = []
    g.append(p)
if g: groups.append(g)
for gi, g in enumerate(groups):
    ls = logs({"address": PM, "topics": [[T_SWAP, T_ML], [p["pid"] for p in g]]}, g[0]["b0"], g[-1]["b0"] + SPAN)
    for x in ls:
        p = pools.get(x["topics"][1]); bn = int(x["blockNumber"], 16)
        if not p or not (p["b0"] <= bn <= p["b0"] + SPAN): continue
        dd = x["data"]; li = int(x["logIndex"], 16); th = x["transactionHash"]
        if x["topics"][0] == T_SWAP:
            if x["topics"][2][-40:] == RELAY: continue
            p["sw"].append((bn, li, s128(W(dd, 0)), s128(W(dd, 1)), W(dd, 2), W(dd, 3), x["topics"][2][-40:], th))
        else:
            p["mls"].append((bn, li, sgn(W(dd, 0)), sgn(W(dd, 1)), sgn(W(dd, 2)), th, x["topics"][2][-40:]))
    print("group", gi, len(groups), flush=True); time.sleep(0.3)
for p in pools.values(): p["sw"].sort(key=lambda x: (x[0], x[1])); p["mls"].sort(key=lambda x: (x[0], x[1]))
pickle.dump(pools, open("fwd_pools.pkl", "wb"))
import collections; print(collections.Counter(p["fam"] for p in pools.values()))
