"""Stage 4b: the whole stretch from the launch to T. Every block L+1 .. T-1 of every pool (full transactions): any transaction other than the
pool's own swaps whose calldata carries the pool's token or pool id (a presigned / copied / failed bot buy would), any transaction to the bot
router or from T's buyer (with its receipt status), any tx from a bot wallet; with offsets from T. Blocks cached in cache/blk.jsonl."""
import pickle, collections
from lib import *
D = pickle.load(open("parsed.pkl", "rb")); P = sorted([p for p in D["pools"] if p["T"] is not None], key=lambda p: p["L"])
kb = KV("blk"); kr = KV("rcp")
botw = {s["eoa"] for p in D["pools"] for s in p["sw"] if s["bot"]}
nb = sorted({b for p in P for b in range(p["L"] + 1, p["Tbn"])})
print("blocks L+1..T-1:", len(nb), "to fetch", sum(1 for b in nb if str(b) not in kb.d), flush=True)
get_blocks(nb, kb, kr, receipts=False)
own = {s["tx"] for p in D["pools"] for s in p["sw"]} | {m["tx"] for p in D["pools"] for m in p["ml"]}
hits = []; router = []; nblk = 0; ntx = 0
for p in P:
    tok = p["token"][2:].lower(); pid = p["pid"][2:].lower()
    for b in range(p["L"] + 1, p["Tbn"]):
        B = kb.d[str(b)]; nblk += 1
        for t in B["txs"]:
            ntx += 1; inp = (t["input"] or "").lower(); to = (t["to"] or "").lower(); fr = (t["from"] or "").lower()
            if t["hash"] in own: continue
            if tok in inp or pid in inp: hits.append((p["L"], p["T"], p["Tbn"] - b, fr[:10], to[:10], inp[:10], "token" if tok in inp else "pool id"))
            if to == BOT or fr == p["buyer"]: router.append([p["L"], p["T"], p["Tbn"] - b, fr[:10], to[:10], inp[:10], t["hash"], fr == p["buyer"], tok in inp])
print(f"pools {len(P)}; blocks scanned {nblk}; transactions {ntx}")
print(f"\ntransactions (not the pool's own swaps / liquidity calls) whose calldata carries this pool's token or pool id, L+1..T-1: {len(hits)}")
for h in hits: print("   ", h)
st = batch([("eth_getTransactionReceipt", [r[6]]) for r in router], 20) if router else []
for r, s in zip(router, st): r.append(s["status"] if s else None)
print(f"\ntransactions to the bot router or from T's buyer in L+1..T-1: {len(router)}; by status {collections.Counter(r[-1] for r in router)}; "
      f"from T's buyer {sum(1 for r in router if r[7])}; carrying the token {sum(1 for r in router if r[8])}")
print("   lead (T - block) of bot-router txs:", sorted(collections.Counter(r[2] for r in router).items()))
print("   selectors:", collections.Counter(r[5] for r in router))
for r in router: 
    if r[-1] != "0x1" or r[7] or r[8]: print("   flagged:", r)
