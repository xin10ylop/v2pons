"""Who funded a wallet: the first block where its balance is non-zero (binary search on historical balance), then the
transaction in that block that names it (as `to`, or inside the input of a disperse call)."""
import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
def first_funded(w, hi):
    lo = 1
    if int(rpc("eth_getBalance", [w, hex(hi)]), 16) == 0 and int(rpc("eth_getTransactionCount", [w, hex(hi)]), 16) == 0: return None
    while lo < hi:
        mid = (lo + hi) // 2
        b = int(rpc("eth_getBalance", [w, hex(mid)]), 16); n = int(rpc("eth_getTransactionCount", [w, hex(mid)]), 16)
        if b > 0 or n > 0: hi = mid
        else: lo = mid + 1
    return lo
out = {}
for w in sys.argv[1:]:
    w = w.lower()
    try:
        b = first_funded(w, 83760000)
    except Exception as e:
        print(w, "error", e); continue
    blk = rpc("eth_getBlockByNumber", [hex(b), True])
    hits = [t for t in blk["transactions"] if (t.get("to") or "").lower() == w or w[2:] in t["input"].lower()]
    ts = int(blk["timestamp"], 16)
    print(w, "first funded block", b, time.strftime("%m-%d %H:%M:%S", time.gmtime(ts)), [(t["hash"][:12], t["from"], t.get("to"), int(t["value"], 16) / 1e18, t["input"][:10]) for t in hits])
    out[w] = {"block": b, "ts": ts, "txs": [(t["hash"], t["from"], t.get("to"), int(t["value"], 16), t["input"][:10]) for t in hits]}
json.dump(out, open("funding_" + "_".join(a[2:8] for a in sys.argv[1:4]) + ".json", "w"))
