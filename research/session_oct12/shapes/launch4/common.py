"""shared constants/helpers for the four new v4 launch shapes (session_oct12/shapes/launch4). Read-only; polite RPC via ./rpc.py
(one POST at a time, >= 0.5 s apart, back-off on 429). Raw caches live in ./cache/ (git-ignored by research/**/cache/)."""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.dont_write_bytecode = True
J = lambda n: os.path.join(HERE, n)
C = lambda n: os.path.join(HERE, "cache", n)
from eth_utils import keccak
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
T_TRANSFER = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x): return x - (1 << 256) if x >= (1 << 255) else x
def utc(ts): return time.strftime("%m-%d %H:%M:%S", time.gmtime(ts))
def jl(p): return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
def pct(v, q):
    v = sorted(v)
    return None if not v else v[min(len(v) - 1, int(q * len(v)))]
# the four shapes of the 15:53 UTC watch, by the last 8 hex digits of the launch transaction's target
SHAPES = {"S1": ["026d2789"], "S2": ["178489c6"], "S3": ["fa61a056"], "S4": ["af0ff9d8", "025c7d37"]}
HOOK_FLAGS = ["afterRemoveLiquidityReturnDelta", "afterAddLiquidityReturnDelta", "afterSwapReturnDelta", "beforeSwapReturnDelta", "afterDonate",
              "beforeDonate", "afterSwap", "beforeSwap", "afterRemoveLiquidity", "beforeRemoveLiquidity", "afterAddLiquidity", "beforeAddLiquidity",
              "afterInitialize", "beforeInitialize"]
def hook_flags(h):
    v = int(h, 16) & 0x3fff
    return [HOOK_FLAGS[i] for i in range(14) if v >> i & 1]
