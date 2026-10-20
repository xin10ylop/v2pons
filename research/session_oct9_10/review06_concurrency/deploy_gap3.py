import json, urllib.request, sys, time, rlp
from eth_utils import keccak
RPC = "https://rpc.mainnet.chain.robinhood.com"; H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
def rpc(m, p, quiet=False):
    for i in range(4):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), H), timeout=30))
            if "result" in r: return r["result"]
            if quiet: return None
            print("err", r); time.sleep(1)
        except Exception as e:
            print("exc", e); time.sleep(2)
    return None
head = int(sys.argv[2])
a = int(sys.argv[1]); b = head
found = []
step = 20000
for s in range(a, b + 1, step):
    logs = rpc("eth_getLogs", [{"fromBlock": hex(s), "toBlock": hex(min(b, s + step - 1)), "address": PM, "topics": [T_INIT, None, "0x" + "0"*64]}]) or []
    for l in logs:
        t = rpc("eth_getTransactionByHash", [l["transactionHash"]])
        if t["input"].startswith("0x2fcb9108"):
            found.append((l, t))
print("head", head, "operator launches in window:", len(found))
for l, t in found[:6]:
    bl = int(l["blockNumber"], 16); frm = t["from"]; to = t["to"].lower(); n = int(t["nonce"], 16)
    cre = None
    for m in range(n - 1, max(-1, n - 6), -1):
        addr = "0x" + keccak(rlp.encode([bytes.fromhex(frm[2:]), m]))[-20:].hex()
        if addr == to: cre = m; break
    code = rpc("eth_getCode", [to, "latest"]) or "0x"; h = keccak(bytes.fromhex(code[2:])).hex()
    info = f"launch block {bl} from {frm[:10]} nonce {n} to {to[:10]} code {len(code)//2-1}B hash {h[:16]} created by from at nonce {cre}"
    if cre is not None:
        # scan back for the creation tx (from == frm, nonce == cre)
        for k in range(0, 400):
            blk = rpc("eth_getBlockByNumber", [hex(bl - k), True])
            hit = [x for x in blk["transactions"] if x["from"].lower() == frm.lower() and int(x["nonce"], 16) == cre]
            if hit:
                info += f"; creation tx in block {bl - k}: {k} blocks before the launch"; break
        else:
            info += "; creation more than 400 blocks before"
    print(info, flush=True)
