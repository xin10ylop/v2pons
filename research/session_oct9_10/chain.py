import json, time, urllib.request, urllib.error
from eth_utils import keccak
RPC = "https://rpc.mainnet.chain.robinhood.com"; H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; UR = "8876789976decbfcbbbe364623c63652db8c0904"; OP = "3194e32622c5d860a0572c74edda99dcfd8fc827"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
W = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16)
def sgn(x): return x - (1 << 256) if x >= (1 << 255) else x
def post(body):
    for i in range(10):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(body).encode(), H), timeout=90))
        except urllib.error.HTTPError as e: time.sleep(4 * (i + 1) if e.code == 429 else 2)
        except Exception: time.sleep(2 + i)
    raise RuntimeError("rpc")
def rpc(m, p):
    r = post({"jsonrpc": "2.0", "id": 1, "method": m, "params": p})
    if "error" in r: raise RuntimeError(str(r["error"])[:200])
    return r["result"]
def batch(calls):
    out = []
    for i in range(0, len(calls), 50):
        ch = calls[i:i+50]
        r = post([{"jsonrpc": "2.0", "id": j, "method": m, "params": p} for j, (m, p) in enumerate(ch)])
        r = sorted(r, key=lambda x: x["id"]); out += [x.get("result") for x in r]
    return out
def logs(flt, a, b):
    try: return rpc("eth_getLogs", [dict(flt, fromBlock=hex(a), toBlock=hex(b))])
    except RuntimeError as e:
        if b <= a: raise
        m = (a + b) // 2; return logs(flt, a, m) + logs(flt, m + 1, b)
def block_at(ts):
    lo, hi = 1, int(rpc("eth_blockNumber", []), 16)
    while lo < hi:
        mid = (lo + hi) // 2
        if int(rpc("eth_getBlockByNumber", [hex(mid), False])["timestamp"], 16) < ts: lo = mid + 1
        else: hi = mid
    return lo
