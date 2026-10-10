"""Out-of-sample: the family's launches after the census head (85,203,897) to now. Initialize logs (PM), launch txs, Swap/ModifyLiquidity
of those pools to now, and the txs of their swaps (all) and adds/pulls. Cached in fresh/."""
import sys, os, json, time; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from common_s import *
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, T_ML, W, sgn
D = os.path.join(HERE, "fresh"); os.makedirs(D, exist_ok=True)
A = 85_203_898
head = int(rpc("eth_blockNumber", []), 16); print("head", head)
fi = os.path.join(D, "inits.json")
inits = json.load(open(fi)) if os.path.exists(fi) else {"to": A - 1, "logs": []}
if inits["to"] < head:
    for a in range(inits["to"] + 1, head + 1, 100_000):
        b = min(a + 99_999, head)
        inits["logs"] += logs({"address": PM, "topics": [T_INIT]}, a, b)
    inits["to"] = head; json.dump(inits, open(fi, "w"))
cand = []
for lg in inits["logs"]:
    c0 = "0x" + lg["topics"][2][-40:]; c1 = "0x" + lg["topics"][3][-40:]
    d = lg["data"]; fee = W(d, 0); ts = sgn(W(d, 1)); hooks = "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3]; sp = W(d, 3); tick = sgn(W(d, 4))
    if c0 == "0x" + "0" * 40 and fee == 500 and ts == 1 and int(hooks, 16) == 0:
        cand.append({"pid": lg["topics"][1], "token": c1, "sqrt_p0": sp, "tick0": tick, "bn": int(lg["blockNumber"], 16), "tx": lg["transactionHash"]})
print("fee500 ts1 hookless ETH inits", len(cand))
txs = batch([("eth_getTransactionByHash", [c["tx"]]) for c in cand])
fam = []
for c, t in zip(cand, txs):
    if t and (t["to"] or "").lower() == PM and t["input"][:10] == "0x6276cbbe" and (len(t["input"]) - 2) // 2 == 196:
        c["from"] = t["from"].lower(); c["nonce"] = int(t["nonce"], 16); fam.append(c)
print("family launches after the census", len(fam))
pids = [c["pid"] for c in fam]
ev = []
for i in range(0, len(pids), 20):
    ch = pids[i:i + 20]; a = min(c["bn"] for c in fam[i:i + 20])
    for lo in range(a, head + 1, 100_000):
        ev += logs({"address": PM, "topics": [[T_SWAP, T_ML], ch]}, lo, min(lo + 99_999, head))
print("events", len(ev))
json.dump({"head": head, "fam": fam, "events": ev}, open(os.path.join(D, "fresh.json"), "w"))
# txs of every swap / modify
hs = sorted({e["transactionHash"] for e in ev})
cp = os.path.join(D, "txs.json"); have = json.load(open(cp)) if os.path.exists(cp) else {}
todo = [h for h in hs if h not in have]; print("txs todo", len(todo))
for i in range(0, len(todo), 500):
    ch = todo[i:i + 500]; res = batch([("eth_getTransactionByHash", [h]) for h in ch])
    for h, t in zip(ch, res):
        if t: have[h] = {"from": t["from"].lower(), "to": (t["to"] or "").lower(), "nonce": int(t["nonce"], 16), "sel": t["input"][2:10], "len": (len(t["input"]) - 2) // 2,
                         "value": int(t["value"], 16), "input": t["input"][:3000]}
    json.dump(have, open(cp, "w")); print(i + len(ch), flush=True); time.sleep(1)
print("done")
