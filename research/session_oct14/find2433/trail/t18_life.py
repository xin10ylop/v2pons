"""A wallet's whole life on another chain: binary search on its nonce through a public archive endpoint (Blast public API), then the
transaction at each nonce and its receipt (to, selector, value, logs). Usage: t18_life.py <chain> <wallet> [days back]. Paced, read-only."""
import sys, json, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/trail")
import xrpc
chain = sys.argv[1]; w = sys.argv[2].lower(); days = float(sys.argv[3]) if len(sys.argv) > 3 else 120
ARCH = {"bsc": "bsc_archive", "ethereum": "eth_archive", "base": "base_archive"}[chain]
BPD = {"bsc": 115200, "ethereum": 7200, "base": 43200}[chain]
def call(m, p, c=ARCH):
    for i in range(10):
        try:
            time.sleep(0.6); return xrpc.call(c, m, p)
        except RuntimeError as e:
            if "429" in str(e) or "rate" in str(e).lower(): time.sleep(5 * (i + 1)); continue
            raise
    raise RuntimeError("gave up")
h = int(call("eth_blockNumber", []), 16)
nonce = lambda b: int(call("eth_getTransactionCount", [w, hex(b)]), 16)
n_now = nonce(h); print(chain, w, "nonce now", n_now, "head", h, flush=True)
prev = max(1, h - int(BPD * days)); out = []
if nonce(prev) > 0: print("nonce already", nonce(prev), "at", prev, "- widen the window"); 
for target in range(nonce(prev), n_now):
    lo, hi = prev, h
    while lo < hi:
        m = (lo + hi) // 2
        if nonce(m) > target: hi = m
        else: lo = m + 1
    prev = lo
    b = call("eth_getBlockByNumber", [hex(lo), True])
    for t in b["transactions"]:
        if t["from"].lower() == w and int(t["nonce"], 16) == target:
            rc = call("eth_getTransactionReceipt", [t["hash"]])
            logs = [(l["address"], l["topics"][0][:10], ["0x" + x[-40:] for x in l["topics"][1:]], l["data"][:66]) for l in rc["logs"]][:6]
            r = {"chain": chain, "nonce": target, "b": lo, "ts": int(b["timestamp"], 16), "utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(int(b["timestamp"], 16))), "to": t.get("to"), "sel": t["input"][:10],
                 "len": (len(t["input"]) - 2) // 2, "v": int(t["value"], 16) / 1e18, "status": rc["status"], "nlogs": len(rc["logs"]), "logs": logs, "h": t["hash"], "inp": t["input"][:330]}
            out.append(r); print(json.dumps(r), flush=True)
json.dump(out, open("/home/user/v2pons/research/session_oct14/find2433/trail/t18_%s_%s.json" % (chain, w[:10]), "w"), indent=0)
