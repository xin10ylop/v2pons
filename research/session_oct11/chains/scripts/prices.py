"""Native-token USD prices from on-chain logs (read-only):
ETH: latest Swap on Base Uniswap v4 ETH/USDC (fee 500, tickSpacing 10, no hooks) pool -> sqrtPriceX96.
BNB: latest Sync on PancakeSwap v2 USDT/WBNB pair -> reserves."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import rpc
from eth_hash.auto import keccak
from eth_abi import encode
OUT = os.path.join(os.path.dirname(__file__), "..", "out")
res = {}
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
pid = "0x" + keccak(encode(["address", "address", "uint24", "int24", "address"],
                           ["0x0000000000000000000000000000000000000000", USDC, 500, 10, "0x0000000000000000000000000000000000000000"])).hex()
url = "https://base-rpc.publicnode.com"; PM = "0x498581fF718922c3f8e6A244956aF099B2652b2b"
SW = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"
h = rpc.block_number(url)
logs = rpc.call(url, "eth_getLogs", [{"fromBlock": hex(h - 300), "toBlock": hex(h), "address": PM, "topics": [SW, pid]}])
l = logs[-1]; sqrtp = int(l["data"][2 + 64 * 2: 2 + 64 * 3], 16)
p = (sqrtp / 2 ** 96) ** 2  # USDC raw per ETH raw
res["ETH_USD"] = round(p * 1e12, 2); res["ETH_src"] = {"poolId": pid, "block": int(l["blockNumber"], 16), "n_swaps_300blk": len(logs)}
url = "https://bsc-rpc.publicnode.com"; PAIR = "0x16b9a82891338f9bA80E2D6970FddA79D1eb0daE"
SYNC = "0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1"
h = rpc.block_number(url)
logs = rpc.call(url, "eth_getLogs", [{"fromBlock": hex(h - 2000), "toBlock": hex(h), "address": PAIR, "topics": [SYNC]}])
l = logs[-1]; r0 = int(l["data"][2:66], 16); r1 = int(l["data"][66:130], 16)
res["BNB_USD"] = round(r0 / r1, 2); res["BNB_src"] = {"pair": PAIR, "block": int(l["blockNumber"], 16), "token0": "USDT(18)", "token1": "WBNB(18)"}
json.dump(res, open(os.path.join(OUT, "prices.json"), "w"), indent=1)
print(res)
