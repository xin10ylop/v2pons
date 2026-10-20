"""Hourly samples of full blocks (1,000 consecutive blocks at the top of each hour, Oct 11 12:00 UTC to the head): every tx to the volume
bot router 0x1cbaf24d (caller, selector, value, calldata) and to the decoy routers; contract creations. Separate block cache."""
import os; os.environ["BLK_CACHE"] = "w07_blk_cache.jsonl"
from common import *
h, th = head()
t0 = 1791720000  # Oct 11 12:00
hours = list(range(t0, th - 200, 3600))
import bisect
bts = sorted((d["ts"], d["b"]) for d in jl(J("w02_bts_cache.jsonl"))) + [(th, h)]
def b_at(t):
    i = bisect.bisect_left([x for x, _ in bts], t); t1, b1 = bts[min(i, len(bts) - 1)]; t0, b0 = bts[max(i - 1, 0)]
    return b0 + int((t - t0) * (b1 - b0) / max(1, t1 - t0))
starts = {t: b_at(t) for t in hours}
OUT = J("w07_sample.jsonl")
done = {json.loads(l)["hour"] for l in open(OUT)} if os.path.exists(OUT) else set()
with open(OUT, "a") as f:
    for t in hours:
        if t in done: continue
        a = starts[t]; bl = get_blocks(list(range(a, min(a + 1000, h))))
        rows = []
        for n in sorted(bl):
            for x in bl[n]["txs"]:
                if x["to"] in (BOT, DECOY_R, FRONT_R2) or x["to"] == "":
                    rows.append({"b": n, "ts": bl[n]["ts"], "f": x["f"], "to": x["to"], "v": x["v"], "nonce": x["nonce"], "sel": x["sel"], "len": x["len"], "h": x["h"], "inp": x["inp"][:1000]})
        f.write(json.dumps({"hour": t, "a": a, "n": len(bl), "ntx": sum(len(b["txs"]) for b in bl.values()), "rows": rows}) + "\n"); f.flush()
        print(utc(t), a, len(bl), len(rows), rpc.STATS, flush=True)
# drop the big block cache afterwards? keep (ignored)
