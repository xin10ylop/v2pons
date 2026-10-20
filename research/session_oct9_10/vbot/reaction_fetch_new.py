"""The same transactions as reaction_fetch.py, for the post-census pools only (newest first), into reaction_new_tx.pkl (merged by reaction.py)."""
import sys, os, json, pickle
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from chain import batch, T_SWAP, W, sgn
from fetch import universe
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
C = pickle.load(open(os.path.join(HERE, "reaction_cache.pkl"), "rb"))
CP = os.path.join(HERE, "reaction_new_tx.pkl")
TX = pickle.load(open(CP, "rb")) if os.path.exists(CP) else {}
cen, nw = universe(); TSW = T_SWAP[-8:]
want = []
for p in sorted(nw, key=lambda p: -p["b0"]):
    ev = sorted(C["logs"][p["pid"]], key=lambda x: (x[0], x[1]))
    pulls = [x for x in ev if not x[2].endswith(TSW) and sgn(W(x[4], 2)) < 0]
    pb = pulls[0][0] if pulls else None
    end = min(pb if pb is not None else 10**12, p["b0"] + 400)
    for x in ev:
        if x[0] > end: break
        if x[2].endswith(TSW) and s128(W(x[4], 0)) < 0: want.append(x[5])
    if pulls: want.append(pulls[0][5])
want = [h for h in dict.fromkeys(want) if h not in TX and h not in C["tx"]]
print("to fetch", len(want), flush=True)
for i in range(0, len(want), 50):
    ch = want[i:i + 50]
    for h, t in zip(ch, batch([("eth_getTransactionByHash", [x]) for x in ch])):
        if t: TX[h] = {"from": t["from"].lower(), "to": (t["to"] or "").lower(), "sel": t["input"][:10], "len": len(t["input"]) // 2 - 1,
                       "value": int(t["value"], 16), "nonce": int(t["nonce"], 16), "bn": int(t["blockNumber"], 16), "idx": int(t["transactionIndex"], 16)}
    pickle.dump(TX, open(CP + ".tmp", "wb")); os.replace(CP + ".tmp", CP)
    print(i + len(ch), flush=True)
print("done", len(TX))
