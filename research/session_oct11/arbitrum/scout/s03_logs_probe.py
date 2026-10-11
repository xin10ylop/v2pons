"""eth_getLogs range/result behaviour, a handful of polite calls per endpoint (no rate stress)."""
import sys, json, collections, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/scout")
from rpc1 import rpc, post, LOG
from eth_utils import keccak
HEAD = 513904384
PM = "0x360e68faccca8ca495c1b759fd9eee466db9fb32"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_POOL = "0x" + keccak(text="PoolCreated(address,address,uint24,int24,address)").hex()
T_SWAP4 = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
EPS = {"arb1": "https://arb1.arbitrum.io/rpc", "publicnode": "https://arbitrum-one-rpc.publicnode.com", "drpc": "https://arbitrum.drpc.org"}
def gl(u, flt, a, b):
    t0 = time.time(); r = rpc(u, "eth_getLogs", [dict(flt, fromBlock=hex(a), toBlock=hex(b))]); dt = time.time() - t0
    if "result" in r: return f"ok n={len(r['result'])} {dt:.2f}s"
    return "ERR " + json.dumps(r.get("error", r))[:220]
for name, u in EPS.items():
    print("==", name)
    for span in (2000, 10000, 100000, 1000000):
        print(" PM Initialize addr-filter span", span, gl(u, {"address": PM, "topics": [T_INIT]}, HEAD - span, HEAD))
    print(" PM Swap span 2000", gl(u, {"address": PM, "topics": [T_SWAP4]}, HEAD - 2000, HEAD))
    print(" PM Swap span 20000", gl(u, {"address": PM, "topics": [T_SWAP4]}, HEAD - 20000, HEAD))
    print(" all-address PM-Swap-topic span 2000", gl(u, {"topics": [T_SWAP4]}, HEAD - 2000, HEAD))
    r = post(u, [{"jsonrpc": "2.0", "id": i, "method": "eth_getBlockByNumber", "params": [hex(HEAD - i), False]} for i in range(5)])
    print(" batch of 5:", ("list of %d, ids %s" % (len(r), [x.get("id") for x in r])) if isinstance(r, list) else str(r)[:200])
    r = post(u, [{"jsonrpc": "2.0", "id": i, "method": "eth_getBlockByNumber", "params": [hex(HEAD - i), False]} for i in range(50)])
    print(" batch of 50:", ("list of %d, errors %d" % (len(r), sum(1 for x in r if 'error' in x))) if isinstance(r, list) else str(r)[:200])
print("requests", len(LOG), "non-ok", [x for x in LOG if x[1] != "ok"])
