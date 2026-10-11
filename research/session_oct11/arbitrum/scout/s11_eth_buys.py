"""ETH/USD from the Arbitrum Chainlink feed; do the quote-paired v4 pools get real buys; characterize the 90%-fee launcher"""
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/scout")
from rpc1 import rpc, post, LOG
from eth_utils import keccak
U = "https://arb1.arbitrum.io/rpc"; HEAD = 513904384
# Chainlink ETH/USD aggregator proxy on Arbitrum One
feed = "0x639fe6ab55c921f74e7fac1ee960c0b6293ba612"
r = rpc(U, "eth_call", [{"to": feed, "data": "0x50d25bcd"}, "latest"])  # latestAnswer()
px = int(r["result"], 16) / 1e8 if "result" in r and isinstance(r.get("result"), str) else None
print("Chainlink ETH/USD:", px)
WETH = "0x82af49447d8a07e3bd95bd0d56f35241523fbab1"; USDC = "0xaf88d065e77c8cc2239327c5edb3a432268e5831"
USDCe = "0xff970a61a04b1ca14834a43f5de4533ebddb5cc8"; USDT = "0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9"; ZERO = "0x"+"0"*40
QUOTES = {ZERO:"ETH", WETH:"WETH", USDC:"USDC", USDCe:"USDC.e", USDT:"USDT"}
W = lambda d,i: int(d[2+64*i:2+64*(i+1)],16)
def sgn(x): return x-(1<<256) if x>=(1<<255) else x
A = lambda t: "0x"+t[26:]
T_SWAP4 = "0x"+keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
dat = json.load(open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/scout/cache/launch_logs_7d.json"))
v4 = dat["logs"]["v4"]; B24 = dat["b24"]
qp = []  # quote-paired pools (exactly one side a quote)
for l in v4:
    c0, c1 = A(l["topics"][2]), A(l["topics"][3]); q0, q1 = c0 in QUOTES, c1 in QUOTES
    if q0 ^ q1:
        qp.append({"pid": l["topics"][1], "quote": QUOTES[c0 if q0 else c1], "bn": l["bn"], "tx": l["tx"], "qside": 0 if q0 else 1})
print("quote-paired v4 pools (7d):", len(qp), "in 24h:", sum(1 for p in qp if p["bn"]>=B24))
# For each pool fetch swaps in [launch, launch+3000] filtered by pool-id topic, count buys (quote into pool)
nbuy = 0; nswap = 0; realbuy_pools = 0
for p in qp:
    r = rpc(U, "eth_getLogs", [{"address":"0x360e68faccca8ca495c1b759fd9eee466db9fb32","topics":[T_SWAP4, p["pid"]],"fromBlock":hex(p["bn"]),"toBlock":hex(min(HEAD,p["bn"]+3000))}])
    sw = r.get("result", []) if isinstance(r, dict) else []
    nswap += len(sw)
    # a buy: quote goes into the pool. amount0,amount1 are int128 (pool's delta). quote side delta > 0 means quote in.
    buys = 0
    for s in sw:
        d = s["data"]; a0 = sgn(W(d,0)); a1 = sgn(W(d,1))
        qd = a0 if p["qside"]==0 else a1
        if qd > 0: buys += 1
    nbuy += buys
    if buys > 0: realbuy_pools += 1
print("quote-paired pools with >=1 buy:", realbuy_pools, "/", len(qp), " total swaps:", nswap, " total buys:", nbuy)
# Dominant 90%-fee launcher: tokens/counterparties of the fee=900000 pools
hi = [l for l in v4 if W(l["data"],0) in (900000,901000)]
print("\n90%-fee launches (fee 900000/901000) 7d:", len(hi))
cp = collections.Counter()
for l in hi:
    c0, c1 = A(l["topics"][2]), A(l["topics"][3])
    cp[(QUOTES.get(c0,"tok"), QUOTES.get(c1,"tok"))] += 1
print("  side types:", cp.most_common())
# sample 3 of these pools: any swaps?
swc = 0
for l in hi[:6]:
    r = rpc(U, "eth_getLogs", [{"address":"0x360e68faccca8ca495c1b759fd9eee466db9fb32","topics":[T_SWAP4, l["topics"][1]],"fromBlock":hex(l["bn"]),"toBlock":hex(min(HEAD,l["bn"]+3000))}])
    swc += len(r.get("result",[]))
print("  swaps in first 6 of those pools (launch+3000):", swc)
print("requests", len(LOG), "non-ok", [x for x in LOG if x[1] != "ok"])
