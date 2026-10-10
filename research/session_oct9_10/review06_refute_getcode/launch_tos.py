import json, urllib.request, sys, time, collections
from eth_utils import keccak
RPC = "https://rpc.mainnet.chain.robinhood.com"; H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
def rpc(m, p):
    for i in range(8):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), H), timeout=30))
            if "result" in r: return r["result"]
            print("err", m, r.get("error"), file=sys.stderr); time.sleep(1)
        except Exception as e:
            print("exc", m, e, file=sys.stderr); time.sleep(1 + i)
    raise RuntimeError(m)
head = int(rpc("eth_blockNumber", []), 16); back = int(sys.argv[1])
rows = []
for s in range(head - back, head + 1, 20000):
    for l in rpc("eth_getLogs", [{"fromBlock": hex(s), "toBlock": hex(min(head, s + 19999)), "address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}]):
        t = rpc("eth_getTransactionByHash", [l["transactionHash"]]); time.sleep(0.15)
        if t["input"].startswith("0x2fcb9108"):
            ts = int(rpc("eth_getBlockByNumber", [l["blockNumber"], False])["timestamp"], 16)
            rows.append((int(l["blockNumber"], 16), ts, t["to"].lower(), t["from"].lower()))
            print(time.strftime("%m-%d %H:%M:%S", time.gmtime(ts)), int(l["blockNumber"], 16), "to", t["to"].lower(), "from", t["from"].lower()[:12], flush=True)
print("head", head, "launches", len(rows), collections.Counter(r[2] == "0x3194e32622c5d860a0572c74edda99dcfd8fc827" for r in rows))
