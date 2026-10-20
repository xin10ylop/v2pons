"""verify the V2/V3 fork factories (code + their creation event seen in the last 7 days) on arb1"""
import sys, json, collections, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/scout")
from rpc1 import rpc, LOG
from eth_utils import keccak
U = "https://arb1.arbitrum.io/rpc"; HEAD = 513904384
T = {"PairCreated": "0x" + keccak(text="PairCreated(address,address,address,uint256)").hex(),
     "PoolCreated": "0x" + keccak(text="PoolCreated(address,address,uint24,int24,address)").hex(),
     "AlgebraPool": "0x" + keccak(text="Pool(address,address,address)").hex(),
     "AlgebraCustomPool": "0x" + keccak(text="CustomPool(address,address,address,address)").hex()}
F = {"uniV2": "0xf1d7cc64fb4452f05c498126312ebe29f30fbcf9", "uniV3": "0x1f98431c8ad98523631ae4a59f267346ea31f984",
     "camelotV2": "0x6eccab422d763ac031210895c81787e87b43a652", "camelotV3(algebra)": "0x1a3c9b1d2f0529d97f2afc5136cc23e58f1fd35b",
     "sushiV2": "0xc35dadb65012ec5796536bd9864ed8773abc74c4", "sushiV3": "0x1af415a1eba07a4986a52b6f2e7de7003d82231e"}
res = {}
for k, a in F.items():
    c = rpc(U, "eth_getCode", [a, "latest"])["result"]; n = (len(c) - 2) // 2
    r = rpc(U, "eth_getLogs", [{"address": a, "fromBlock": hex(HEAD - 1_000_000), "toBlock": hex(HEAD)}])
    if "result" in r:
        tc = collections.Counter(l["topics"][0] for l in r["result"]); names = {v: kk for kk, v in T.items()}
        res[k] = {"addr": a, "code_bytes": n, "logs_1M": len(r["result"]), "topics": {names.get(t, t[:10]): c for t, c in tc.items()}}
    else: res[k] = {"addr": a, "code_bytes": n, "err": str(r)[:200]}
    print(k, res[k])
json.dump(res, open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/scout/s04_factories.json", "w"), indent=1)
print("requests", len(LOG), "non-ok", [x for x in LOG if x[1] != "ok"])
