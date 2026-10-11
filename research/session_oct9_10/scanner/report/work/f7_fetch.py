"""Copy of skeptic s7_fresh_fetch.py (v3.0/v5.0/v2.433 launches after the census to the head, their events to +3,000 and first txs), cached to report/work/fresh2.
(fee, tick spacing, hooks 0, the exact sqrtP); their Swap + ModifyLiquidity logs to +3,000 (or head); the txs of each pool's first 10 swaps and first pull.
Cached to fresh/ (re-run resumes)."""
import sys, os, json
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, T_ML, W, sgn
HERE = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/report/work"
D = HERE + "/fresh2"; os.makedirs(D, exist_ok=True)
FP = {(10000, 200, 679394651928963067279918579724198): "v3.0", (10000, 200, 526364174002223567019744861584709): "v5.0", (2500, 50, 1604517591721945638372359205383840): "v2.433"}
A = 85203898
head = int(rpc("eth_blockNumber", []), 16)
f_init = D + "/inits.json"
if os.path.exists(f_init): inits = json.load(open(f_init))
else:
    inits = []
    for a in range(A, head + 1, 100000):
        inits += logs({"address": PM, "topics": [T_INIT]}, a, min(head, a + 99999))
    json.dump({"head": head, "logs": inits}, open(f_init, "w")); inits = {"head": head, "logs": inits}
H = inits["head"]; L = inits["logs"]
pools = []
for l in L:
    if int(l["topics"][2], 16) != 0: continue
    fee = int(l["data"][2:66], 16); ts = sgn(int(l["data"][66:130], 16)); hooks = l["data"][130 + 24:194]; sp = W(l["data"], 3)
    k = FP.get((fee, ts, sp))
    if k and int(hooks, 16) == 0:
        pools.append({"pid": l["topics"][1], "sub": k, "b0": int(l["blockNumber"], 16), "tx": l["transactionHash"], "token": "0x" + l["topics"][3][-40:], "fee": fee, "sp0": sp})
print("head", H, "inits", len(L), {k: sum(1 for p in pools if p["sub"] == k) for k in ("v3.0", "v5.0", "v2.433")})
f_ev = D + "/events.json"
ev = json.load(open(f_ev)) if os.path.exists(f_ev) else {}
todo = [p for p in pools if p["pid"] not in ev]
for i in range(0, len(todo), 20):
    g = todo[i:i + 20]; a = min(p["b0"] for p in g); b = min(H, max(p["b0"] for p in g) + 3000)
    if b - a > 60000:
        g = g[:1]; a = g[0]["b0"]; b = min(H, a + 3000)
    lg = logs({"address": PM, "topics": [[T_SWAP, T_ML], [p["pid"] for p in g]]}, a, b)
    for p in g: ev[p["pid"]] = {"to": min(H, p["b0"] + 3000), "logs": []}
    for l in lg:
        if l["topics"][1] in ev and int(l["blockNumber"], 16) <= ev[l["topics"][1]]["to"]:
            ev[l["topics"][1]]["logs"].append({"bn": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "t": l["topics"][0], "data": l["data"], "tx": l["transactionHash"], "sender": l["topics"][2]})
    json.dump(ev, open(f_ev, "w"))
print("events", len(ev))
f_tx = D + "/txs.json"
txs = json.load(open(f_tx)) if os.path.exists(f_tx) else {}
want = set(p["tx"] for p in pools)
for p in pools:
    lg = sorted(ev[p["pid"]]["logs"], key=lambda x: (x["bn"], x["li"]))
    sw = [x for x in lg if x["t"] == T_SWAP][:10]; ml = [x for x in lg if x["t"] == T_ML and sgn(W(x["data"], 2)) < 0][:1]
    want |= set(x["tx"] for x in sw + ml)
need = [h for h in want if h not in txs]
for i in range(0, len(need), 50):
    res = batch([("eth_getTransactionByHash", [h]) for h in need[i:i + 50]])
    for h, r in zip(need[i:i + 50], res):
        if r: txs[h] = {"from": r["from"], "to": r["to"], "value": int(r["value"], 16), "input": r["input"], "nonce": int(r["nonce"], 16), "bn": int(r["blockNumber"], 16), "ti": int(r["transactionIndex"], 16)}
    if i % 500 == 0: json.dump(txs, open(f_tx, "w"))
json.dump(txs, open(f_tx, "w"))
json.dump(pools, open(D + "/pools.json", "w"))
print("txs", len(txs), "missing", sum(1 for h in want if h not in txs))
