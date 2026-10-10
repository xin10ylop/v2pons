"""operator launches (Initialize with ETH as currency0, tx input 0x2fcb9108) in the last N blocks, and for each the launcher's creation block
(binary search on eth_getCode at past blocks), i.e. the deploy-to-call gap"""
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
            print("err", m, r.get("error"), file=sys.stderr); time.sleep(1)
        except Exception as e:
            print("exc", m, e, file=sys.stderr); time.sleep(1 + i)
    raise RuntimeError(m)
head = int(rpc("eth_blockNumber", []), 16); back = int(sys.argv[1])
found = []
for s in range(head - back, head + 1, 20000):
    for l in rpc("eth_getLogs", [{"fromBlock": hex(s), "toBlock": hex(min(head, s + 19999)), "address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}]):
        t = rpc("eth_getTransactionByHash", [l["transactionHash"]])
        if t["input"].startswith("0x2fcb9108"):
            found.append((int(l["blockNumber"], 16), t["to"].lower(), int(rpc("eth_getBlockByNumber", [l["blockNumber"], False])["timestamp"], 16)))
print("head", head, "launches in last", back, "blocks:", len(found))
for bl, to, ts in found:
    lo, hi = bl - 2000, bl                              # code present at hi; find the first block with code
    try:
        if rpc("eth_getCode", [to, hex(lo)]) != "0x":
            print(bl, to, "created more than 2000 blocks before"); continue
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if rpc("eth_getCode", [to, hex(mid)]) != "0x": hi = mid
            else: lo = mid
        print(time.strftime("%H:%M:%S", time.gmtime(ts)), "launch", bl, "launcher", to[:12], "created in", hi, "gap", bl - hi, flush=True)
    except Exception as e:
        print(bl, to, "lookup failed", e)
