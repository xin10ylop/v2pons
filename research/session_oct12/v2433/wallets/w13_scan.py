"""Lean forward/backward full-block scan (no block cache): every tx from or to any of the given addresses, from block a for n blocks
(negative n scans backward); stops when every address in --stop has sent a tx with nonce >= its stop nonce. Appends hits to w13_hits.jsonl."""
from common import *
import argparse
ap = argparse.ArgumentParser(); ap.add_argument("a", type=int); ap.add_argument("n", type=int); ap.add_argument("addrs")
ap.add_argument("--stop", default=""); ap.add_argument("--tag", default="")
A = ap.parse_args()
addrs = {x.lower() for x in A.addrs.split(",")}
stop = {x.split(":")[0].lower(): int(x.split(":")[1]) for x in A.stop.split(",") if x}
got = {}
OUT = J("w13_hits.jsonl"); step = 25
blocks = list(range(A.a, A.a + A.n)) if A.n > 0 else list(range(A.a, A.a + A.n, -1))
with open(OUT, "a") as f:
    for i in range(0, len(blocks), step):
        ch = blocks[i:i + step]
        res = rpc.batch("eth_getBlockByNumber", [[hex(x), True] for x in ch], n=step)
        for b in res:
            if not b: continue
            n = int(b["number"], 16); ts = int(b["timestamp"], 16)
            for t in b["transactions"]:
                fr = t["from"].lower(); to = (t.get("to") or "").lower()
                if fr in addrs or to in addrs:
                    r = {"tag": A.tag, "b": n, "ts": ts, "f": fr, "to": to, "v": str(int(t["value"], 16)), "nonce": int(t["nonce"], 16), "sel": t["input"][:10], "len": (len(t["input"]) - 2) // 2, "h": t["hash"]}
                    f.write(json.dumps(r) + "\n"); f.flush()
                    print(n, utc(ts), fr, "->", to, int(t["value"], 16) / 1e18, "nonce", r["nonce"], r["sel"], r["len"], t["hash"], flush=True)
                    if fr in stop and r["nonce"] >= stop[fr]: got[fr] = True
        if stop and all(k in got for k in stop): print("stop condition met at", ch[-1]); break
        if i % 2000 == 0: print("..", ch[-1], rpc.STATS, flush=True)
print("scanned through", ch[-1], rpc.STATS)
