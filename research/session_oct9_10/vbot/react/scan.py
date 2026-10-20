#!/usr/bin/env python3
"""Full-block scan [a, b]: every tx (hash, from, to, value, nonce, selector, calldata length, prio) per block -> vbot/scan_<a>_<b>.pkl."""
import sys, os, pickle, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from chain import batch, rpc
a, b = int(sys.argv[1]), int(sys.argv[2]); P = os.path.join(HERE, f"scan_{a}_{b}.pkl")
BL = pickle.load(open(P, "rb")) if os.path.exists(P) else {}
need = [n for n in range(a, b + 1) if n not in BL]; t0 = time.time()
for i in range(0, len(need), 200):
    ch = need[i:i + 200]
    for n, blk in zip(ch, batch([("eth_getBlockByNumber", [hex(n), True]) for n in ch])):
        if blk: BL[n] = (int(blk["timestamp"], 16), [(x["hash"], x["from"].lower(), (x.get("to") or "").lower(), int(x["value"], 16), int(x["nonce"], 16), x["input"][:10], (len(x["input"]) - 2) // 2, int(x.get("maxPriorityFeePerGas") or "0x0", 16)) for x in blk["transactions"]])
    if i % 4000 == 0:
        pickle.dump(BL, open(P + ".tmp", "wb")); os.replace(P + ".tmp", P); print(i, len(need), f"{time.time() - t0:.0f}s", flush=True)
pickle.dump(BL, open(P + ".tmp", "wb")); os.replace(P + ".tmp", P); print("done", len(BL), flush=True)
