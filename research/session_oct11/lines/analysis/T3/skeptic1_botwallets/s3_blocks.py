"""Stage 3: every full block (all transactions: sender, target, selector, value, calldata length, nonce, index) in [L+1, T+3] of each pool with a
bot buy, and [L+1, L+70] of each pool without one -> cache/blk.jsonl (slim). These are the blocks in which an engine following the rule could
see a bot-wallet transaction and fire."""
import pickle
from lib import *
D = pickle.load(open("parsed.pkl", "rb")); P = D["pools"]
kv = KV("blk")
need = []
for p in P:
    hi = p["Tbn"] + 3 if p["T"] is not None else p["L"] + 70
    need += list(range(p["L"] + 1, hi + 1))
need = [n for n in dict.fromkeys(need) if str(n) not in kv.d]
print("blocks to fetch", len(need), flush=True)
def slim(b):
    return {"n": int(b["number"], 16), "ts": int(b["timestamp"], 16),
            "tx": [[t["hash"], (t.get("from") or "").lower(), (t.get("to") or "").lower(), (t.get("input") or "")[2:10], int(t["value"], 16),
                    (len(t.get("input") or "0x") - 2) // 2, int(t["nonce"], 16), int(t["transactionIndex"], 16)] for t in b["transactions"]]}
for i in range(0, len(need), 200):
    ch = need[i:i + 200]
    res = batch([("eth_getBlockByNumber", [hex(n), True]) for n in ch], 25)
    for n, b in zip(ch, res):
        if b: kv.put(str(n), slim(b))
    kv.flush()
    if (i // 200) % 10 == 0: print(f"  {i + len(ch)}/{len(need)}", flush=True)
print("have", sum(1 for n in need if str(n) in kv.d), "of", len(need))
