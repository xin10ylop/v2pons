"""Stage 3: whole blocks (every transaction, i.e. what the sequencer feed carries) [L+1, T+3] of every 3.0 pool with a bot buy -> cache/blk.jsonl
(seeded read-only from the sibling's cache of the same public-RPC answers; missing blocks fetched). Then an integrity check: 60 random seeded
blocks re-fetched fresh from the public RPC and compared (block hash list of transactions, from/to/input/value)."""
import pickle, random
from lib import *
D = pickle.load(open("parsed.pkl", "rb"))
P = [p for p in D["pools"] if p["T"] is not None]
kb = KV("blk"); print("block cache: seeded", kb.seeded, flush=True)
nums = sorted(set(b for p in P for b in range(p["L"] + 1, p["Tbn"] + 4)))
miss = [n for n in nums if str(n) not in kb.d]
print("pools", len(P), "blocks", len(nums), "missing", len(miss), flush=True)
for i in range(0, len(miss), 500):
    get_blocks(miss[i:i + 500], kb, None, receipts=False)
    print(f"  blocks {min(i + 500, len(miss))}/{len(miss)}", flush=True)
random.seed(6); sample = random.sample([n for n in nums if str(n) in kb.d], 60)
fresh = batch([("eth_getBlockByNumber", [hex(n), True]) for n in sample], 20)
bad = 0
for n, b in zip(sample, fresh):
    a = kb.d[str(n)]; f = slim_block(b)
    ka = [(t["hash"], t["from"], t["to"], t["input"], t["value"]) for t in a["txs"]]; kf = [(t["hash"], t["from"], t["to"], t["input"], t["value"]) for t in f["txs"]]
    if ka != kf or a["ts"] != f["ts"]: bad += 1; print("  MISMATCH", n)
print(f"integrity: {len(sample) - bad} of {len(sample)} re-fetched blocks identical to the cache", flush=True)
