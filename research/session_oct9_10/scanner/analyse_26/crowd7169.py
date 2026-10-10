"""the 7169b574 crowd routers: is calldata word 6 the swap's ETH in, what is word 7 (minOut?), who signs, who pays (tx value), recipient = signer?"""
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); T = load_txs()
tx7 = {h: t for h, t in T.items() if t["selector"] == "7169b574"}
print("7169b574 txs in census:", len(tx7), "routers", collections.Counter(t["to"] for t in tx7.values()).most_common(8))
pids = set(r[0] for t in tx7.values() for r in t["refs"])
E = load_events(pids)
fam = collections.Counter(P[p]["family"] for p in pids)
print("pools touched", len(pids), "families top", fam.most_common(8))
m = collections.Counter(); w7 = collections.Counter(); val = collections.Counter(); rec = collections.Counter(); w1 = collections.Counter(); w9 = collections.Counter(); sell = 0
nonces = []; signers = collections.Counter()
for h, t in tx7.items():
    inp = t.get("input") or t["input512"]
    W = lambda i: int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16)
    sw = [s for pid, kind, rank in t["refs"] if kind == "swap" for s in E[pid]["swaps"] if s["tx"] == h]
    for s in sw:
        if s["a0"] < 0: m[W(6) == -s["a0"]] += 1
        else: sell += 1; m[("sell", W(6) == s["a1"] * -1, W(6) == -s["a1"])] += 1
    w7[W(7)] += 1; val[t["value_wei"]] += 1; rec[("0x" + inp[10 + 64 * 5 + 24: 10 + 64 * 6]) == t["from"]] += 1; w1["0x" + inp[10 + 64 * 1 + 24: 10 + 64 * 2]] += 1; w9[(W(8), W(9))] += 1
    nonces.append(t["nonce"]); signers[t["from"]] += 1
print("word6 == ETH in:", m)
print("word7 values:", w7.most_common(5))
print("tx value:", val.most_common(4))
print("recipient(word5) == signer:", rec)
print("word1 (target router):", w1.most_common(3), "words 8,9:", w9.most_common(4))
nonces.sort(); print("signer nonces p10/50/90", nonces[len(nonces) // 10], nonces[len(nonces) // 2], nonces[9 * len(nonces) // 10], "distinct signers", len(signers), "top", signers.most_common(3))
