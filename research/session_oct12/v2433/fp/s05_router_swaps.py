"""Every PoolManager Swap whose sender (topic 2, the contract that called PoolManager.swap) is the volume bot's router 0x1cbaf24d or the decoy
router 0x65050a9b, from s01's start block to its head. Cached in s05_swaps_cache.jsonl (resumable by block)."""
import json
from common import R, PM, T_SWAP, BOT, p, load_jsonl, append_jsonl
DECOY = "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc"
meta = json.load(open(p("s01_meta.json")))
done = {}
try: done = json.load(open(p("s05_meta.json")))
except Exception: pass
for who, addr in (("bot", BOT), ("decoy", DECOY)):
    a0 = done.get(who, meta["start"] - 1) + 1
    for a in range(a0, meta["head"] + 1, 20000):
        b = min(a + 19999, meta["head"])
        ls = R.logs({"address": PM, "topics": [T_SWAP, None, "0x" + "0" * 24 + addr[2:]]}, a, b)
        append_jsonl("s05_swaps_cache.jsonl", [{"who": who, "b": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "h": l["transactionHash"], "pid": l["topics"][1], "d": l["data"]} for l in ls])
        done[who] = b; json.dump(done, open(p("s05_meta.json"), "w"))
    print(who, "done to", done[who], R.STATS, flush=True)
print("rows", len(load_jsonl("s05_swaps_cache.jsonl")))
