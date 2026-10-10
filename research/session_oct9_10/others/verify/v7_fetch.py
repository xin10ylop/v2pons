#!/usr/bin/env python3
"""Verifier step 7 fetch: (a) timestamps of the post-census original-launcher launches and the first 6 real-buy txs on each (crowd
signature); (b) our relay's swaps since the census head (did the bot trade them?); (c) 6 recurring crowd wallets: every token the
PoolManager sent them from Oct 8 00:00 to now; (d) the pull txs of 6 PM1444 v5.0 and 6 v2.433 pools. Cache: verify/cache_v7.pkl"""
import sys, os, json, pickle, random
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, SCR)
from chain import rpc, batch, logs, PM, T_SWAP, T_ML, W, sgn
from eth_utils import keccak
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
T_TR = "0x" + keccak(text="Transfer(address,address,uint256)").hex(); pad = lambda a: "0x" + "0" * 24 + a[2:].lower()
CP = os.path.join(HERE, "cache_v7.pkl"); C = pickle.load(open(CP, "rb")) if os.path.exists(CP) else {}
def save(): pickle.dump(C, open(CP, "wb"))
post = json.load(open(os.path.join(HERE, "v6_post.json"))); P = pickle.load(open(os.path.join(HERE, "cache_post.pkl"), "rb"))
head = P["head"]
ours = [r for r in post if r["fam"] == "OURS-orig"]
if "ts" not in C:
    bl = batch([("eth_getBlockByNumber", [hex(r["b0"]), False]) for r in ours] + [("eth_getBlockByNumber", [hex(84125769), False]), ("eth_getBlockByNumber", [hex(head), False])])
    C["ts"] = {int(b["number"], 16): int(b["timestamp"], 16) for b in bl if b}; save()
if "crowd" not in C:
    need = []
    for r in ours:
        ev = sorted(P["plogs"].get(r["pid"], []), key=lambda x: (x[0], x[1]))
        need += [th for bn, li, t0, snd, d, th in ev if t0 == T_SWAP and s128(W(d, 0)) <= -2 * 10**14][:6]
    C["crowd"] = {}
    for i in range(0, len(need), 50):
        ch = need[i:i + 50]
        for h, t in zip(ch, batch([("eth_getTransactionByHash", [x]) for x in ch])):
            if t: C["crowd"][h] = {"from": t["from"].lower(), "to": (t["to"] or "").lower(), "inlen": (len(t["input"]) - 2) // 2, "prio": int(t.get("maxPriorityFeePerGas") or "0x0", 16), "nonce": int(t["nonce"], 16)}
    save()
if "relay" not in C:
    C["relay"] = logs({"address": PM, "topics": [T_SWAP, None, pad("0x2abb5653352f6b2f3b4f4261877cd02d9e05a957")]}, 84238620, head); save()
if "trace" not in C:
    ct = json.load(open(os.path.join(HERE, "..", "crowdtrace.json")))
    random.seed(3); ws = random.sample(ct["crowd_wallets"], 6)
    C["trace"] = {"wallets": ws, "logs": []}
    a = 82878144
    while a <= head:
        b = min(a + 199999, head); C["trace"]["logs"] += logs({"topics": [T_TR, pad(PM), [pad(w) for w in ws]]}, a, b); a = b + 1
    save()
if "pulls" not in C:
    R = {json.loads(l)["pid"]: json.loads(l) for l in open(os.path.join(HERE, "..", "census.jsonl"))}
    pick = []
    for cond in (lambda r: r["fee"] == 10000 and round(r["value"] or 0, 3) == 5.0, lambda r: r["fee"] == 2500 and r["ts"] == 50):
        xs = [r for r in R.values() if r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and cond(r) and r.get("pull_tx")]
        random.seed(9); pick += random.sample(xs, 6)
    C["pulls"] = [(r["pid"], r["from"], r["nonce"], t["from"], (t["to"] or ""), t["input"][:10], int(t["nonce"], 16)) for r, t in zip(pick, batch([("eth_getTransactionByHash", [r["pull_tx"]]) for r in pick]))]
    save()
print("done")
