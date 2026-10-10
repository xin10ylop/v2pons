import json, sys, time, urllib.request
from eth_utils import keccak
RPC = "https://rpc.mainnet.chain.robinhood.com"; H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
def post(b):
    for i in range(6):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(b).encode(), H), timeout=60))
        except Exception as e: time.sleep(2 + 2*i)
    raise RuntimeError("rpc")
def rpc(m, p):
    r = post({"jsonrpc": "2.0", "id": 1, "method": m, "params": p})
    if "error" in r: raise RuntimeError(str(r["error"]))
    return r["result"]
a, b = int(sys.argv[1]), int(sys.argv[2])
inits = []
x = a
while x <= b:
    y = min(b, x + 20000)
    try:
        inits += rpc("eth_getLogs", [{"address": PM, "topics": [T_INIT, None, "0x" + "0"*64], "fromBlock": hex(x), "toBlock": hex(y)}])
    except Exception as e:
        print("logs err", e); 
    x = y + 1
print("inits", len(inits))
n = 0
for l in inits:
    t = rpc("eth_getTransactionByHash", [l["transactionHash"]])
    if not t["input"].startswith("0x2fcb9108"): continue
    lb = int(l["blockNumber"], 16); to = t["to"]
    code = rpc("eth_getCode", [to, hex(lb)]); h = keccak(bytes.fromhex(code[2:])).hex()
    # find the first block with code by binary search over [lb-20000, lb]
    lo, hi = max(0, lb - 200000), lb
    while lo < hi:
        m = (lo + hi) // 2
        c = rpc("eth_getCode", [to, hex(m)])
        if len(c) > 2: hi = m
        else: lo = m + 1
    blk = rpc("eth_getBlockByNumber", [hex(lo), False]); lblk = rpc("eth_getBlockByNumber", [hex(lb), False])
    print(f"launch blk {lb} launcher {to} deployed blk {lo} gap {lb - lo} blocks ({int(lblk['timestamp'],16) - int(blk['timestamp'],16)} s) codelen {len(code)//2-1} hash {h[:16]} txidx {t['transactionIndex']} from {t['from']}")
    n += 1
    if n >= int(sys.argv[3]): break
