"""Block headers (timestamp, tx count) around each pool's L and T: L-1, L, T-2..T+1 (3.0 and 5.0 first, then 2.433). -> blocks.jsonl (cache)"""
import json, pickle, os
from rpc import batch
D = pickle.load(open("cache/data.pkl", "rb")); pools = D["pools"]
have = {}
if os.path.exists("blocks.jsonl"):
    for l in open("blocks.jsonl"): x = json.loads(l); have[x["n"]] = x
need = []
for line in ("3.0", "5.0", "2.433"):
    for p in pools:
        if p["line"] != line: continue
        bs = [p["L"] - 1, p["L"]] + ([p["Tbn"] - 2, p["Tbn"] - 1, p["Tbn"], p["Tbn"] + 1] if p["Tbn"] else [])
        need += [b for b in bs if b not in have and b not in need]
print(len(need), "blocks to fetch", flush=True)
f = open("blocks.jsonl", "a")
for i in range(0, len(need), 100):
    ch = need[i:i + 100]
    res = batch([("eth_getBlockByNumber", [hex(b), False]) for b in ch], size=20)
    for b, h in zip(ch, res):
        if h: f.write(json.dumps({"n": b, "ts": int(h["timestamp"], 16), "ntx": len(h["transactions"]), "l1": int(h["l1BlockNumber"], 16)}) + "\n")
    f.flush(); print(i + len(ch), flush=True)
