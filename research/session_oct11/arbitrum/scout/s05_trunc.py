"""does arb1 truncate large getLogs ranges silently? compare 1 x 1M with 10 x 100k; probe the result cap with PoolManager Swap"""
import sys, json, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/scout")
from rpc1 import rpc, LOG
from eth_utils import keccak
U = "https://arb1.arbitrum.io/rpc"; HEAD = 513904384
PM = "0x360e68faccca8ca495c1b759fd9eee466db9fb32"; V3F = "0x1f98431c8ad98523631ae4a59f267346ea31f984"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP4 = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
def gl(flt, a, b):
    r = rpc(U, "eth_getLogs", [dict(flt, fromBlock=hex(a), toBlock=hex(b))])
    return r["result"] if "result" in r else r
for nm, flt in (("PM Initialize", {"address": PM, "topics": [T_INIT]}), ("V3 factory", {"address": V3F})):
    one = gl(flt, HEAD - 1_000_000 + 1, HEAD); parts = []
    for i in range(10):
        a = HEAD - 1_000_000 + 1 + i * 100_000; p = gl(flt, a, a + 99_999); parts += p if isinstance(p, list) else []
    print(nm, "1x1M:", len(one) if isinstance(one, list) else one, " 10x100k:", len(parts),
          " first/last block", (int(parts[0]["blockNumber"], 16), int(parts[-1]["blockNumber"], 16)) if parts else None)
for span in (50_000, 200_000):
    t0 = time.time(); r = gl({"address": PM, "topics": [T_SWAP4]}, HEAD - span, HEAD)
    print("PM Swap span", span, ("n=%d" % len(r)) if isinstance(r, list) else json.dumps(r)[:300], f"{time.time()-t0:.1f}s")
print("requests", len(LOG), "non-ok", [x for x in LOG if x[1] != "ok"])
