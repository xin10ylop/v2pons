"""Skeptic 1, step 3: the txs the exit clock depends on and the pull txs.
- every Swap in [lb + 2, lb + 80] that puts >= 0.004 ETH of WETH into a WETH-token0 pool (a buy big enough to be the engine's trigger once
  its calldata word or value is read: the a0193551 crowd call swaps 99% of its word);
- the tx of each pool's first Burn with liquidity > 0 (who pulled, through what).
-> k03_txs_cache.jsonl"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpc
from eth_utils import keccak
HERE = os.path.dirname(os.path.abspath(__file__))
tp = lambda s: "0x" + keccak(text=s).hex()
T_SW = tp("Swap(address,address,int256,int256,uint160,uint128,int24)"); T_BU = tp("Burn(address,int24,int24,uint128,uint256,uint256)")
WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
def S(h):
    x = int(h, 16); return x - (1 << 256) if x >> 255 else x
D = json.load(open(os.path.join(HERE, "k01_launches.json"))); L = {x["pool"]: x for x in D["line"]}
win, burns = {}, []
for line in open(os.path.join(HERE, "k02_events_cache.jsonl")):
    r = json.loads(line)
    if r["kind"] == "win": win[r["pool"]] = r["logs"]
    else: burns = r["logs"]
want = set()
for p, logs in win.items():
    x = L[p]
    if x["token0"] != WETH: continue
    for l in logs:
        bn = int(l["blockNumber"], 16)
        if l["topics"][0] == T_SW and x["lb"] + 2 <= bn <= x["lb"] + 80 and S(l["data"][2:66]) >= 4 * 10 ** 15:
            want.add(l["transactionHash"])
first = {}
for l in sorted(burns, key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
    if int(l["data"][2:66], 16) > 0: first.setdefault(l["address"].lower(), l["transactionHash"])
want |= set(first.values())
want = sorted(want)
print(f"txs to fetch: {len(want)} ({len(first)} first-burn txs)")
txs = rpc.batch("eth_getTransactionByHash", [[h] for h in want], n=20)
with open(os.path.join(HERE, "k03_txs_cache.jsonl"), "w") as f:
    for h, t in zip(want, txs):
        f.write(json.dumps({"hash": h, "tx": t}) + "\n")
print("saved", rpc.STATS)
