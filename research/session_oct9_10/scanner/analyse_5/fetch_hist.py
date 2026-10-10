"""opC before the census window: every ETH-paired v4 Initialize with fee 100 (ts 1) or 500 (ts 10) and no hooks in the N x 100k blocks
before block 83,520,210, filtered by data alone (no tx fetch yet). Cache: hist_inits.json (per 100k chunk)."""
import sys, os, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import logs, PM, T_INIT, W, sgn
START = 83_520_210; N = int(sys.argv[1]) if len(sys.argv) > 1 else 15
cf = os.path.join(HERE, "hist_inits.json")
cache = json.load(open(cf)) if os.path.exists(cf) else {}
Z = "0x" + "0" * 64
for i in range(1, N + 1):
    a = START - 100_000 * i; b = a + 99_999
    if str(a) in cache: continue
    ls = logs({"address": PM, "topics": [T_INIT, None, Z]}, a, b)
    keep = []
    for l in ls:
        d = l["data"]; fee = W(d, 0); ts = sgn(W(d, 1)); hooks = W(d, 2); sp = W(d, 3); tick = sgn(W(d, 4))
        if hooks == 0 and (fee, ts) in ((100, 1), (500, 10)):
            keep.append({"pid": l["topics"][1], "token": "0x" + l["topics"][3][-40:], "fee": fee, "ts": ts, "sqrt_p": sp, "tick": tick, "bn": int(l["blockNumber"], 16), "tx": l["transactionHash"]})
    cache[str(a)] = {"n_all": len(ls), "keep": keep}
    json.dump(cache, open(cf, "w"))
    print(a, b, len(ls), len(keep), flush=True)
