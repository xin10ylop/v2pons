"""After the census (block 85,881,750 to the head): every PoolManager Initialize with ETH as currency0, fee 100, tick spacing 1, no hook;
its launch tx (POSM, ac9650d8, 2,276 bytes, value 0 = C-1); per pool: Swap and ModifyLiquidity logs to now (pulled or not, buys).
-> fresh.json. Read-only: eth_blockNumber, eth_getLogs, eth_getTransactionByHash."""
import rpc
from common import *
from eth_utils import keccak
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
W = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16)
sgn = lambda x: x - (1 << 256) if x >= (1 << 255) else x
head = int(rpc.call("eth_blockNumber", []), 16); start = 85_881_751
inits = []
for a in range(start, head + 1, 20_000):
    ls = rpc.call("eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(min(head, a + 19_999)), "address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}])
    for l in ls:
        d = l["data"]
        if W(d, 0) == 100 and sgn(W(d, 1)) == 1 and int(d[2 + 64*2: 2 + 64*3], 16) == 0:
            inits.append({"pid": l["topics"][1], "token": "0x" + l["topics"][3][-40:], "bn": int(l["blockNumber"], 16), "tx": l["transactionHash"], "sqrt": W(d, 3), "tick": sgn(W(d, 4))})
print(f"head {head}; fee-100/ts-1/no-hook ETH inits since the census: {len(inits)}")
txs = rpc.batch("eth_getTransactionByHash", [[x["tx"]] for x in inits])
c1 = []
for x, t in zip(inits, txs):
    x["to"] = t["to"].lower(); x["value"] = int(t["value"], 16); x["clen"] = (len(t["input"]) - 2) // 2; x["sel"] = t["input"][2:10]; x["from"] = t["from"].lower()
    x["c1"] = x["to"] == POSM and x["sel"] == "ac9650d8" and x["clen"] == 2276 and x["value"] == 0
    if x["c1"]: c1.append(x)
print(f"C-1 shaped: {len(c1)}; others: {C.Counter((x['to'][:10], x['sel'], x['clen'], x['value']) for x in inits if not x['c1']).most_common(5)}")
for x in c1:
    ls = rpc.call("eth_getLogs", [{"fromBlock": hex(x["bn"]), "toBlock": hex(head), "address": PM, "topics": [[T_SWAP, T_ML], x["pid"]]}])
    sw = [l for l in ls if l["topics"][0] == T_SWAP]; ml = [l for l in ls if l["topics"][0] == T_ML]
    x["n_swaps"] = len(sw); x["adds"] = sum(1 for l in ml if sgn(W(l["data"], 2)) > 0); x["pulls"] = [int(l["blockNumber"], 16) for l in ml if sgn(W(l["data"], 2)) < 0]
    x["buys"] = [(int(l["blockNumber"], 16) - x["bn"], sgn(W(l["data"], 0)) / -1e18) for l in sw if sgn(W(l["data"], 0)) < 0]
    x["last"] = (W(sw[-1]["data"], 2), W(sw[-1]["data"], 3)) if sw else None
    x["age"] = head - x["bn"]
    print(f"  {x['pid'][:12]} token {x['token']} block {x['bn']} age {x['age']} swaps {x['n_swaps']} buys>=0.02 at +{[b for b, e in x['buys'] if e >= 0.02][:3]} pulls {[p - x['bn'] for p in x['pulls']]} sqrt0 {x['sqrt']}")
json.dump({"head": head, "c1": c1}, open(os.path.join(V, "fresh.json"), "w"))
print(rpc.STATS)
