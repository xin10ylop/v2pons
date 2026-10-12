"""S02: every Swap/Mint/Burn of the WETH-side 13ead562 pools from the launch block to +W (default 5000) or the head, and the txs behind
the mint(s), every swap to +400 and every burn (public RPC, read-only, polite) -> s02_events.json"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpc
from eth_utils import keccak
OUT = os.path.dirname(os.path.abspath(__file__))
WIN = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
tp = lambda s: "0x" + keccak(text=s).hex()
T_SW = tp("Swap(address,address,int256,int256,uint160,uint128,int24)"); T_MI = tp("Mint(address,address,int24,int24,uint128,uint256,uint256)")
T_BU = tp("Burn(address,int24,int24,uint128,uint256,uint256)")
D = json.load(open(os.path.join(OUT, "s01_launches.json")))
head = int(rpc.call("eth_blockNumber", []), 16)
L = [x for x in D["launches"] if x["qs"] is not None]
prm = [[{"address": x["pool"], "topics": [[T_SW, T_MI, T_BU]], "fromBlock": hex(x["lb"]), "toBlock": hex(min(x["lb"] + WIN, head))}] for x in L]
res = rpc.batch("eth_getLogs", prm, n=10)
want = set()
for x, ls in zip(L, res):
    if ls is None:   # fall back to the splitting single call
        ls = rpc.logs({"address": x["pool"], "topics": [[T_SW, T_MI, T_BU]]}, x["lb"], min(x["lb"] + WIN, head))
    x["ev_to"] = min(x["lb"] + WIN, head); x["logs"] = sorted(ls, key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    for l in x["logs"]:
        off = int(l["blockNumber"], 16) - x["lb"]
        if l["topics"][0] in (T_MI, T_BU) or off <= 400: want.add(l["transactionHash"])
want = sorted(want)
txs = rpc.batch("eth_getTransactionByHash", [[h] for h in want])
json.dump({"head": head, "win": WIN, "launches": L, "txs": dict(zip(want, txs))}, open(os.path.join(OUT, "s02_events.json"), "w"))
print(f"head {head}: {len(L)} pools, {sum(len(x['logs']) for x in L)} logs, {len(want)} txs; rpc {rpc.STATS}")
