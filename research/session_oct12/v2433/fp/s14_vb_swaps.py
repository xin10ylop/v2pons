"""Every Swap in the volume bot's pools (VB 2.4333 / 3.0 / 5.0 launched in the window) made through the Universal Router (the bot router's
buys and its wallets' sells both go through it), launch to launch + 6,000 blocks; 40 pool ids per query (topic OR-list). Cached in s14_swaps_cache.jsonl."""
import json
from clusters import load
from common import R, PM, T_SWAP, UR, p, load_jsonl, append_jsonl
meta = json.load(open(p("s01_meta.json")))
rows = sorted([r for r in load() if r["fam"].split(" (")[0] in ("VB 2.4333", "VB 3.0", "VB 5.0")], key=lambda r: r["b"])
try: done = set(json.load(open(p("s14_meta.json"))))
except Exception: done = set()
for i in range(0, len(rows), 40):
    ch = rows[i:i + 40]; key = ch[0]["pid"]
    if key in done: continue
    a, b = ch[0]["b"], min(ch[-1]["b"] + 6000, meta["head"])
    ls = R.logs({"address": PM, "topics": [T_SWAP, [r["pid"] for r in ch], "0x" + "0" * 24 + UR[2:]]}, a, b)
    append_jsonl("s14_swaps_cache.jsonl", [{"b": int(l["blockNumber"], 16), "li": int(l["logIndex"], 16), "h": l["transactionHash"], "pid": l["topics"][1], "d": l["data"]} for l in ls])
    done.add(key); json.dump(sorted(done), open(p("s14_meta.json"), "w"))
    print(i + len(ch), len(ls), R.STATS, flush=True)
