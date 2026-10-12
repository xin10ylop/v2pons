"""Skeptic 1, step 2: each launch pool's Initialize/Swap/Mint/Burn logs in [lb, lb + 120] (one getLogs per pool, JSON-RPC batches), and
every Burn of the pools from their launch to the frozen head (for the pull counts). Raw logs -> k02_events_cache.jsonl (ignored by git)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpc
from eth_utils import keccak
HERE = os.path.dirname(os.path.abspath(__file__))
tp = lambda s: "0x" + keccak(text=s).hex()
T_SW = tp("Swap(address,address,int256,int256,uint160,uint128,int24)"); T_MI = tp("Mint(address,address,int24,int24,uint128,uint256,uint256)")
T_BU = tp("Burn(address,int24,int24,uint128,uint256,uint256)"); T_IN = tp("Initialize(uint160,int24)")
D = json.load(open(os.path.join(HERE, "k01_launches.json"))); head = D["head"]; L = sorted(D["line"], key=lambda x: x["lb"])
WIN = 120
plist = [[{"address": x["pool"], "topics": [[T_IN, T_SW, T_MI, T_BU]], "fromBlock": hex(x["lb"]), "toBlock": hex(min(head, x["lb"] + WIN))}] for x in L]
res = rpc.batch("eth_getLogs", plist, n=10)
out = open(os.path.join(HERE, "k02_events_cache.jsonl"), "w")
n = 0
for x, r in zip(L, res):
    assert r is not None, x["pool"]
    out.write(json.dumps({"pool": x["pool"], "kind": "win", "logs": r}) + "\n"); n += len(r)
print(f"window logs {n} for {len(L)} pools")
burns = []
for i in range(0, len(L), 40):
    ch = L[i:i + 40]; a0 = ch[0]["lb"]
    for a in range(a0, head + 1, 300000):
        burns += rpc.logs({"address": [x["pool"] for x in ch], "topics": [T_BU]}, a, min(a + 299999, head))
out.write(json.dumps({"kind": "burns", "head": head, "logs": burns}) + "\n"); out.close()
print(f"burns to head {len(burns)}", rpc.STATS)
