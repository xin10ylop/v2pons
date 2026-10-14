"""Shared constants and helpers for the find2433 census (read-only, public Robinhood RPC via rpc.py, >= 0.5 s between POSTs)."""
import sys, os, json, glob as _glob, bisect, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rpc
from eth_utils import keccak
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
BOT = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
V3F = "0x1f7d7550b1b028f7571e69a784071f0205fd2efa"
WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
USDG = "0x5fc5360d0400a0fd4f2af552add042d716f1d168"
NPM3 = "0x73991a25c818bf1f1128deaab1492d45638de0d3"
E = "0x" + "0" * 40
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
T_TRANSFER = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
T_V3POOL = "0x" + keccak(text="PoolCreated(address,address,uint24,int24,address)").hex()
T_V3INIT = "0x" + keccak(text="Initialize(uint160,int24)").hex()
T_V3SWAP = "0x" + keccak(text="Swap(address,address,int256,int256,uint160,uint128,int24)").hex()
T_V3MINT = "0x" + keccak(text="Mint(address,address,int24,int24,uint128,uint256,uint256)").hex()
T_V3BURN = "0x" + keccak(text="Burn(address,int24,int24,uint128,uint256,uint256)").hex()
V2433 = 2433328500000000000
SQRTP_2433 = 1604517591721945638372359205383840
LIQ_2433 = 49279426163460954002188
ZERO32 = "0x" + "0" * 64
def W(d, i): return int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x, bits=256): return x - (1 << bits) if x >= (1 << (bits - 1)) else x
def P(name): return os.path.join(HERE, name)
def jload(p):
    with open(P(p)) as f: return json.load(f)
def jdump(o, p):
    with open(P(p), "w") as f: json.dump(o, f, separators=(",", ":"))
def jl_load(p):
    fp = P(p)
    if not os.path.exists(fp): return []
    with open(fp) as f: return [json.loads(l) for l in f if l.strip()]
def jl_append(rows, p):
    with open(P(p), "a") as f:
        for r in rows: f.write(json.dumps(r, separators=(",", ":")) + "\n")
def hm(t): return time.strftime("%m-%d %H:%M:%S", time.gmtime(t))
class BT:
    """block -> unix time by interpolation over sampled blocks (s01_blocks_cache.jsonl)"""
    def __init__(self):
        bl = sorted((r["b"], r["t"]) for r in jl_load("s01_blocks_cache.jsonl")); self.bl = bl; self.bb = [b for b, _ in bl]
    def __call__(self, b):
        bl, bb = self.bl, self.bb; i = bisect.bisect_left(bb, b)
        if i < len(bb) and bb[i] == b: return bl[i][1]
        if i == 0: return bl[0][1]
        if i >= len(bb): return bl[-1][1] + (b - bb[-1]) / 9.84
        (b0, t0), (b1, t1) = bl[i - 1], bl[i]
        return t0 + (t1 - t0) * (b - b0) / (b1 - b0)

def launches():
    """the s04 launch table (one row per v4 Initialize / V3 PoolCreated)"""
    return jl_load("s04_launches_cache.jsonl")
