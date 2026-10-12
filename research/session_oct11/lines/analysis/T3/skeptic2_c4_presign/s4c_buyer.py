"""Stage 4c: anything about T's buyer wallet before T: a transaction to it or carrying its address in calldata in L+1..T-1 (a funding
transfer), its ETH balance and nonce at L, T-12, T-4, T-1 were meant to show an internal funding, but the public node keeps no historical state
("historical state ... is not available"), so only the transaction-level check is made."""
import pickle, collections
from lib import *
D = pickle.load(open("parsed.pkl", "rb")); P = sorted([p for p in D["pools"] if p["T"] is not None], key=lambda p: p["L"])
kb = KV("blk")
own = {s["tx"] for p in D["pools"] for s in p["sw"]}
hits = []
for p in P:
    a = p["buyer"][2:]
    for b in range(p["L"] + 1, p["Tbn"]):
        for t in kb.d[str(b)]["txs"]:
            if (t["to"] or "").lower() == p["buyer"] or a in (t["input"] or "").lower(): hits.append((p["L"], p["Tbn"] - b, t["from"][:10], (t["to"] or "")[:10], t["input"][:10], int(t["value"], 16) / 1e18))
print(f"transactions to T's buyer or with its address in calldata, L+1..T-1: {len(hits)}", hits[:20])
print("balance / nonce history: not available on the public node (non-archive: historical state is not available); buyer nonces at T:", sorted(p["buyer_nonce"] for p in P))
