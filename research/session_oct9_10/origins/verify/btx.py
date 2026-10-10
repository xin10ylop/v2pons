"""Base: fetch txs by hash (from, to, value, nonce, block, time, input head)."""
import sys, json, time, urllib.request
RPC = "https://mainnet.base.org"; H = {"Content-Type": "application/json", "User-Agent": "curl/8.5.0"}
def post(b):
    for i in range(8):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(b).encode(), H), timeout=60))
        except Exception as e: err = e; time.sleep(2 + 2 * i)
    raise RuntimeError(str(err))
hs = sys.argv[1:]
r = post([{"jsonrpc": "2.0", "id": i, "method": "eth_getTransactionByHash", "params": [h]} for i, h in enumerate(hs)])
for x in sorted(r, key=lambda x: x["id"]):
    t = x.get("result")
    if not t: print(hs[x["id"]], "NOT FOUND", x.get("error")); continue
    b = int(t["blockNumber"], 16)
    blk = post({"jsonrpc": "2.0", "id": 1, "method": "eth_getBlockByNumber", "params": [hex(b), False]})["result"]
    print(json.dumps({"hash": t["hash"][:18], "block": b, "utc": time.strftime("%m-%d %H:%M:%S", time.gmtime(int(blk["timestamp"], 16))), "from": t["from"], "to": t["to"], "eth": int(t["value"], 16) / 1e18, "nonce": int(t["nonce"], 16), "input": t["input"][:140]}))
    time.sleep(0.3)
