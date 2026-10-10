import json, urllib.request, sys, time
from eth_utils import keccak
RPC = "https://rpc.mainnet.chain.robinhood.com"; H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
def rpc(m, p):
    for i in range(6):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), H), timeout=30))
            if "result" in r: return r["result"]
            print("err", r); time.sleep(2)
        except Exception as e:
            print("exc", e); time.sleep(2)
    raise RuntimeError(m)
a = int(sys.argv[1]); b = int(sys.argv[2])
logs = rpc("eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(b), "address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}])
n = 0
for l in logs:
    t = rpc("eth_getTransactionByHash", [l["transactionHash"]])
    if not t["input"].startswith("0x2fcb9108"): continue
    to = t["to"]; bl = int(l["blockNumber"], 16)
    code = rpc("eth_getCode", [to, hex(bl)]); h = keccak(bytes.fromhex(code[2:])).hex()
    lo, hi = bl - 20000, bl
    if rpc("eth_getCode", [to, hex(lo)]) != "0x":
        print(to, "deployed before", lo); continue
    while hi - lo > 1:
        m = (lo + hi) // 2
        if rpc("eth_getCode", [to, hex(m)]) != "0x": hi = m
        else: lo = m
    print(f"launch block {bl} tx {t['hash'][:12]} to {to} code {len(code)//2-1}B hash {h[:16]} deployed at block {hi}: {bl - hi} blocks before the launch")
    n += 1
    if n >= 6: break
