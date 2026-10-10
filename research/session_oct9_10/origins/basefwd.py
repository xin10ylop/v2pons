"""Base (8453) public RPC: given a Relay fill tx hash and its recipient, scan forward blocks for the recipient's next tx (where the bridged ETH went).
Usage: basefwd.py fill_tx recipient [maxblocks]"""
import sys, json, time, urllib.request, urllib.error
RPC = "https://mainnet.base.org"; H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
def post(b):
    for i in range(8):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(b).encode(), H), timeout=60))
        except urllib.error.HTTPError as e: time.sleep(2 + 2 * i)
        except Exception: time.sleep(2 + i)
    raise RuntimeError("rpc")
def rpc(m, p): return post({"jsonrpc": "2.0", "id": 1, "method": m, "params": p})["result"]
fill, rcp = sys.argv[1], sys.argv[2].lower(); mx = int(sys.argv[3]) if len(sys.argv) > 3 else 600
t = rpc("eth_getTransactionByHash", [fill]); b0 = int(t["blockNumber"], 16)
print("fill block", b0, "from", t["from"], "to", t["to"], int(t["value"], 16) / 1e18, flush=True)
for s in range(b0, b0 + mx, 5):
    r = post([{"jsonrpc": "2.0", "id": j, "method": "eth_getBlockByNumber", "params": [hex(s + j), True]} for j in range(5)])
    for x in sorted(r, key=lambda x: x["id"]):
        blk = x.get("result")
        if not blk: continue
        for tx in blk["transactions"]:
            if tx["from"].lower() == rcp or (tx.get("to") or "").lower() == rcp:
                print(int(blk["number"], 16), time.strftime("%m-%d %H:%M:%S", time.gmtime(int(blk["timestamp"], 16))), tx["from"], "->", tx.get("to"), int(tx["value"], 16) / 1e18, "nonce", int(tx["nonce"], 16), tx["input"][:10], tx["hash"], flush=True)
                if tx["from"].lower() == rcp: raise SystemExit(0)
    time.sleep(0.3)
print("not found within", mx, "blocks")
