"""shared constants/helpers for the C-1 reaction study (session_oct12/c1). Read-only; polite RPC via ./rpc.py (one POST >= 0.5 s apart)."""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.dont_write_bytecode = True
J = lambda n: os.path.join(HERE, n)
from eth_utils import keccak
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
ROUTER = "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"
WALLET = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
SQRTP = 792280926924313289846529216293289; LIQ = 100000088127620690885293
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x): return x - (1 << 256) if x >= (1 << 255) else x
def utc(ts): return time.strftime("%m-%d %H:%M:%S", time.gmtime(ts))
def jl(p): return [json.loads(l) for l in open(p)]
def pct(v, q):
    v = sorted(v)
    return None if not v else v[min(len(v) - 1, int(q * len(v)))]
def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 1.0)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))
def cp_upper(k, n, a=0.05):
    """one-sided Clopper-Pearson upper bound (exact, via bisection on the binomial cdf)"""
    from math import comb
    if k >= n: return 1.0
    cdf = lambda p: sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
    lo, hi = k / n, 1.0
    for _ in range(60):
        m = (lo + hi) / 2
        if cdf(m) > a: lo = m
        else: hi = m
    return hi
