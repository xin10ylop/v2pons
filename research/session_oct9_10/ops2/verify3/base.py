"""Base (8453) public RPC helper for following Relay cash-out recipients (historical nonce binary search)."""
import json, urllib.request, time
U = "https://mainnet.base.org"; HD = {"Content-Type": "application/json", "User-Agent": "curl/8.5.0"}
def rpc(m, p):
    for i in range(8):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(U, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), HD), timeout=60))
            if "error" in r: raise RuntimeError(str(r["error"])[:200])
            time.sleep(0.25); return r["result"]
        except urllib.error.HTTPError as e:
            time.sleep(2 + 2 * i)
    raise RuntimeError("base rpc")
