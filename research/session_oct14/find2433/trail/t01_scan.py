"""Lean full-block scan (no full block cache): blocks [a, b] (or backward), keeps every tx from/to the watched addresses, plus (with --native)
every plain ETH transfer (input 0x) and every contract creation, as compact rows in <out>_cache.jsonl. Stops early when every --stop
address has sent a tx with nonce <= its stop nonce (backward) or >= (forward)."""
from common import *
import argparse
ap = argparse.ArgumentParser(); ap.add_argument("a", type=int); ap.add_argument("b", type=int); ap.add_argument("addrs")
ap.add_argument("--out", default="t01_scan"); ap.add_argument("--native", action="store_true"); ap.add_argument("--back", action="store_true")
ap.add_argument("--stop", default=""); ap.add_argument("--per", type=int, default=25)
A = ap.parse_args()
addrs = {x.lower() for x in A.addrs.split(",") if x}
stop = {x.split(":")[0].lower(): int(x.split(":")[1]) for x in A.stop.split(",") if x}
got = set()
OUT = J(A.out + "_cache.jsonl"); DONE = J(A.out + "_done_cache.jsonl")
done = set()
for r in jl(DONE): done.update(range(r["a"], r["b"] + 1))
blocks = [n for n in range(A.a, A.b + 1) if n not in done]
if A.back: blocks = blocks[::-1]
print("blocks to read", len(blocks), flush=True)
nh = 0
with open(OUT, "a") as f, open(DONE, "a") as fd:
    for i in range(0, len(blocks), A.per):
        ch = blocks[i:i + A.per]
        res = rpc.batch("eth_getBlockByNumber", [[hex(x), True] for x in ch], n=A.per)
        ok = []
        for x, b in zip(ch, res):
            if not b: continue
            ok.append(x)
            n = int(b["number"], 16); ts = int(b["timestamp"], 16)
            for t in b["transactions"]:
                fr = t["from"].lower(); to = (t.get("to") or "").lower(); inp = t["input"]
                watched = fr in addrs or to in addrs
                if watched or (A.native and (inp == "0x" or not to)):
                    r = {"b": n, "ts": ts, "f": fr, "to": to, "v": str(int(t["value"], 16)), "nonce": int(t["nonce"], 16), "sel": inp[:10], "len": (len(inp) - 2) // 2, "h": t["hash"], "w": int(watched)}
                    f.write(json.dumps(r) + "\n"); nh += 1
                    if watched:
                        print(n, utc(ts), fr, "->", to, int(t["value"], 16) / 1e18, "nonce", r["nonce"], r["sel"], r["len"], t["hash"], flush=True)
                        if fr in stop and ((A.back and r["nonce"] <= stop[fr]) or (not A.back and r["nonce"] >= stop[fr])): got.add(fr)
        if ok: fd.write(json.dumps({"a": min(ok), "b": max(ok)}) + "\n"); fd.flush()
        f.flush()
        if stop and all(k in got for k in stop): print("stop condition met at", ch[-1]); break
        if (i // A.per) % 80 == 0: print("..", ch[-1], rpc.STATS, "rows", nh, flush=True)
print("scanned through", ch[-1], rpc.STATS, "rows", nh)
