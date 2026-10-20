"""Base (chain 8453) forward tracer via public RPC with historical state: for an address, find each outgoing tx (nonce increments)
in [lo, hi] by binary search on eth_getTransactionCount, then read that block's txs from the address.
usage: bfwd.py addr lo_block [max_txs]"""
import sys, json, time, urllib.request
RPC = "https://mainnet.base.org"
def rpc(m, p):
    for i in range(8):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), {"Content-Type": "application/json", "User-Agent": "curl/8.5.0"}), timeout=60))
            if "error" in r: raise RuntimeError(str(r["error"])[:200])
            return r["result"]
        except Exception as e:
            err = e; time.sleep(1.5 * (i + 1))
    raise RuntimeError(str(err))
def nonce(a, b): return int(rpc("eth_getTransactionCount", [a, hex(b)]), 16)
def bal(a, b="latest"): return int(rpc("eth_getBalance", [a, hex(b) if isinstance(b, int) else b]), 16) / 1e18
a = sys.argv[1].lower(); lo = int(sys.argv[2]); mx = int(sys.argv[3]) if len(sys.argv) > 3 else 5
head = int(rpc("eth_blockNumber", []), 16)
n_lo = nonce(a, lo); n_hi = nonce(a, head)
print(f"{a} nonce at {lo}: {n_lo}, at head {head}: {n_hi}, balance now {bal(a):.6f}", flush=True)
cur = lo
for k in range(n_lo, min(n_hi, n_lo + mx)):
    L, H = cur, head
    while L < H:   # first block where nonce > k
        M = (L + H) // 2
        if nonce(a, M) > k: H = M
        else: L = M + 1
    blk = rpc("eth_getBlockByNumber", [hex(L), True])
    for t in blk["transactions"]:
        if t["from"].lower() == a and int(t["nonce"], 16) == k:
            print(json.dumps({"nonce": k, "block": L, "ts": int(blk["timestamp"], 16), "to": t.get("to"), "eth": int(t["value"], 16) / 1e18, "sel": t["input"][:10], "hash": t["hash"]}), flush=True)
    cur = L
