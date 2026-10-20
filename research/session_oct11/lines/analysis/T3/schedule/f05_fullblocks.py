"""Full blocks (every transaction: from, to, value, selector, input length, nonce, gas price) for the most recent N 3.0/5.0 pools:
T-8..T (the window where a 1-4 block precursor would sit) and a control window L+8..L+16 (quiet pre-T blocks of the same pool).
-> fullblocks.jsonl (cache; one line per block, transactions slimmed)"""
import json, pickle, os, sys
from rpc import batch
N = int(sys.argv[1]) if len(sys.argv) > 1 else 120
D = pickle.load(open("cache/data.pkl", "rb")); pools = D["pools"]
P = [p for p in pools if p["line"] in ("3.0", "5.0") and p["T"] is not None and p["T"] >= 26][-N:]
have = set()
if os.path.exists("cache/fullblocks.jsonl"):
    for l in open("cache/fullblocks.jsonl"): have.add(json.loads(l)["n"])
need = []
for p in P:
    for b in list(range(p["Tbn"] - 8, p["Tbn"] + 1)) + list(range(p["L"] + 8, p["L"] + 17)):
        if b not in have and b not in need: need.append(b)
print(len(P), "pools;", len(need), "blocks", flush=True)
f = open("cache/fullblocks.jsonl", "a")
for i in range(0, len(need), 60):
    ch = need[i:i + 60]
    res = batch([("eth_getBlockByNumber", [hex(b), True]) for b in ch], size=10)
    for b, h in zip(ch, res):
        if not h: continue
        txs = [{"h": t["hash"], "i": int(t["transactionIndex"], 16), "from": t["from"].lower(), "to": (t.get("to") or "").lower(), "v": int(t["value"], 16),
                "sel": t["input"][2:10], "len": (len(t["input"]) - 2) // 2, "nonce": int(t["nonce"], 16), "gp": int(t.get("gasPrice") or "0x0", 16),
                "type": t.get("type"), "in": t["input"][:330]} for t in h["transactions"]]
        f.write(json.dumps({"n": b, "ts": int(h["timestamp"], 16), "txs": txs}) + "\n")
    f.flush(); print(i + len(ch), flush=True)
print("done", flush=True)
