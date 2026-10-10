"""Base: who funded address X (first block where balance > 0, binary search with historical state), print the funding tx(s)."""
import sys, json, time, urllib.request
RPC = "https://mainnet.base.org"; H = {"Content-Type": "application/json", "User-Agent": "curl/8.5.0"}
def rpc(m, p):
    for i in range(8):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), H), timeout=60))
            if "error" in r: raise RuntimeError(str(r["error"])[:200])
            return r["result"]
        except Exception as e: err = e; time.sleep(1.5 * (i + 1))
    raise RuntimeError(str(err))
x = sys.argv[1].lower(); hi = int(sys.argv[2]); lo = hi - int(sys.argv[3]) if len(sys.argv) > 3 else hi - 5000
bal = lambda b: int(rpc("eth_getBalance", [x, hex(b)]), 16)
if bal(lo) > 0: print("already funded at", lo); sys.exit()
L, Hh = lo, hi
while L < Hh:
    M = (L + Hh) // 2
    if bal(M) > 0: Hh = M
    else: L = M + 1
blk = rpc("eth_getBlockByNumber", [hex(L), True])
for t in blk["transactions"]:
    if (t.get("to") or "").lower() == x: print(json.dumps({"block": L, "ts": blk["timestamp"], "from": t["from"], "nonce": int(t["nonce"], 16), "eth": int(t["value"], 16) / 1e18, "sel": t["input"][:10], "hash": t["hash"]}))
print("funded at block", L, "(if no tx printed: internal transfer)")
