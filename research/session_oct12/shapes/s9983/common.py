"""shared constants/helpers for the 9983bb8c launch shape (session_oct12/shapes/s9983). Read-only; polite RPC via ./rpc.py
(a copy of c1/rpc.py: one POST at a time, >= 0.5 s apart, back-off on 429; log in cache/). Raw caches live in ./cache/ (git-ignored)."""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.dont_write_bytecode = True
J = lambda n: os.path.join(HERE, n)
C = lambda n: os.path.join(HERE, "cache", n)
from eth_utils import keccak
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
USDG = "0x5fc5360d0400a0fd4f2af552add042d716f1d168"
Z = "0x" + "0" * 40
QUOTE = "0x32ac8c1d7672667d5ebdea22935f7b06fc8d496f"      # currency0 of the shape (census v4_currency0_top: 54 inits in the Oct 9-10 census)
TARGET_TAIL = "9983bb8c"; HOOK_TAIL = "4924e0cc"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
T_DONATE = "0x" + keccak(text="Donate(bytes32,address,uint256,uint256)").hex()
T_TRANSFER = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
T_APPROVAL = "0x" + keccak(text="Approval(address,address,uint256)").hex()
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x): return x - (1 << 256) if x >= (1 << 255) else x
def utc(ts): return time.strftime("%m-%d %H:%M:%S", time.gmtime(ts))
def jl(p): return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
def pct(v, q):
    v = sorted(v)
    return None if not v else v[min(len(v) - 1, int(q * len(v)))]
def topic_addr(a): return "0x" + "0" * 24 + a[2:].lower()
HOOK_FLAGS = ["afterRemoveLiquidityReturnDelta", "afterAddLiquidityReturnDelta", "afterSwapReturnDelta", "beforeSwapReturnDelta", "afterDonate",
              "beforeDonate", "afterSwap", "beforeSwap", "afterRemoveLiquidity", "beforeRemoveLiquidity", "afterAddLiquidity", "beforeAddLiquidity",
              "afterInitialize", "beforeInitialize"]
def hook_flags(h):
    v = int(h, 16) & 0x3fff
    return [HOOK_FLAGS[i] for i in range(14) if v >> i & 1]
def sel(sig): return keccak(text=sig).hex()[:8]
