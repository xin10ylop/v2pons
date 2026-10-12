"""Every ERC20 Transfer whose recipient is the volume bot's router 0x1cbaf24d (it receives the bought tokens from the PoolManager, then passes
them to its wallet) or whose sender is it, s01's start to its head, any token. Cached in s06_bot_transfers_cache.jsonl."""
import json
from common import R, T_TRANSFER, BOT, p, load_jsonl, append_jsonl
meta = json.load(open(p("s01_meta.json")))
pad = "0x" + "0" * 24 + BOT[2:]
try: done = json.load(open(p("s06_meta.json")))
except Exception: done = {}
for side, topics in (("to", [T_TRANSFER, None, pad]), ("from", [T_TRANSFER, pad])):
    a0 = done.get(side, meta["start"] - 1) + 1
    for a in range(a0, meta["head"] + 1, 20000):
        b = min(a + 19999, meta["head"])
        ls = R.logs({"topics": topics}, a, b)
        append_jsonl("s06_bot_transfers_cache.jsonl", [{"side": side, "b": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "h": l["transactionHash"], "token": l["address"].lower(),
                                                        "t1": l["topics"][1], "t2": l["topics"][2], "d": l["data"]} for l in ls])
        done[side] = b; json.dump(done, open(p("s06_meta.json"), "w"))
    print(side, "done", R.STATS, flush=True)
print("rows", len(load_jsonl("s06_bot_transfers_cache.jsonl")))
