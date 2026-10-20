import json, sys, time, urllib.request, rlp
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
def batch(calls):
    r = post([{"jsonrpc": "2.0", "id": j, "method": m, "params": p} for j, (m, p) in enumerate(calls)])
    return [x.get("result") for x in sorted(r, key=lambda x: x["id"])]
a, b = int(sys.argv[1]), int(sys.argv[2])
inits = []
x = a
while x <= b:
    y = min(b, x + 20000)
    inits += rpc("eth_getLogs", [{"address": PM, "topics": [T_INIT, None, "0x" + "0"*64], "fromBlock": hex(x), "toBlock": hex(y)}])
    x = y + 1
print("inits", len(inits))
n = 0
for l in inits:
    t = rpc("eth_getTransactionByHash", [l["transactionHash"]])
    if not t["input"].startswith("0x2fcb9108"): continue
    lb = int(l["blockNumber"], 16); to = t["to"].lower(); frm = t["from"].lower(); non = int(t["nonce"], 16)
    cands = {"0x" + keccak(rlp.encode([bytes.fromhex(frm[2:]), k])).hex()[-40:]: k for k in range(max(0, non - 5), non)}
    found = None
    for start in range(lb, lb - 3000, -50):
        blks = batch([("eth_getBlockByNumber", [hex(bn), True]) for bn in range(start, start - 50, -1)])
        for bk in blks:
            if not bk: continue
            for tx in bk["transactions"]:
                if tx["from"].lower() == frm and int(tx["nonce"], 16) < non and (tx["to"] is None):
                    rc = rpc("eth_getTransactionReceipt", [tx["hash"]])
                    if (rc.get("contractAddress") or "").lower() == to:
                        found = (int(bk["number"], 16), int(bk["timestamp"], 16), tx["hash"])
                if found: break
            if found: break
        if found: break
    lblk = rpc("eth_getBlockByNumber", [hex(lb), False])
    print(f"launch blk {lb} from {frm[:10]} nonce {non} launcher {to} create-addr-match {to in cands} deploy {found and found[0]} gap_blocks {found and lb - found[0]} gap_s {found and int(lblk['timestamp'],16) - found[1]}")
    sys.stdout.flush()
    n += 1
    if n >= int(sys.argv[3]): break
