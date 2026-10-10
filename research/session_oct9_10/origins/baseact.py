"""Base public RPC: every tx from/to an address in blocks [a, a+n). Usage: baseact.py addr a n"""
import sys, json, time, urllib.request, urllib.error
RPC = "https://mainnet.base.org"; H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
def post(b):
    for i in range(8):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(b).encode(), H), timeout=60))
        except urllib.error.HTTPError as e: time.sleep(2 + 2 * i)
        except Exception: time.sleep(2 + i)
    raise RuntimeError("rpc")
w = sys.argv[1].lower(); a = int(sys.argv[2]); n = int(sys.argv[3])
cnt = 0
for s in range(a, a + n, 5):
    r = post([{"jsonrpc": "2.0", "id": j, "method": "eth_getBlockByNumber", "params": [hex(s + j), True]} for j in range(5)])
    for x in sorted(r, key=lambda x: x["id"]):
        blk = x.get("result")
        if not blk: continue
        for tx in blk["transactions"]:
            if tx["from"].lower() == w or (tx.get("to") or "").lower() == w:
                cnt += 1
                print(int(blk["number"], 16), time.strftime("%m-%d %H:%M:%S", time.gmtime(int(blk["timestamp"], 16))), tx["from"], "->", tx.get("to"), round(int(tx["value"], 16) / 1e18, 6), "nonce", int(tx["nonce"], 16), tx["input"][:10], tx["hash"][:18], flush=True)
    time.sleep(0.25)
print("txs", cnt, "in", n, "blocks from", a)
