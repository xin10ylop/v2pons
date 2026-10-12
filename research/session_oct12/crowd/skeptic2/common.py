"""skeptic2 shared helpers (own code; constants from REPORT_W / the task)."""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.dont_write_bytecode = True
J = lambda n: os.path.join(HERE, n)
from eth_utils import keccak
tp = lambda s: "0x" + keccak(text=s).hex()
FACT = "0x1f7d7550b1b028f7571e69a784071f0205fd2efa"; NPM = "0x73991a25c818bf1f1128deaab1492d45638de0d3"
WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"; UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
T_PC = tp("PoolCreated(address,address,uint24,int24,address)"); T_SW = tp("Swap(address,address,int256,int256,uint160,uint128,int24)")
T_BU = tp("Burn(address,int24,int24,uint128,uint256,uint256)"); T_MI = tp("Mint(address,address,int24,int24,uint128,uint256,uint256)")
T_TR = tp("Transfer(address,address,uint256)")
CROWD_SHAPES = {("3593564c", 484), ("a0193551", 452), ("49f74a5d", 452)}
def si(h):
    x = int(h, 16); return x - (1 << 256) if x >> 255 else x
def word(d, i): return d[2 + 64 * i: 2 + 64 * (i + 1)]
def utc(ts): return time.strftime("%m-%d %H:%M:%S", time.gmtime(ts))
def jl(p):
    out = []
    if not os.path.exists(p): return out
    for l in open(p):
        try: out.append(json.loads(l))
        except ValueError: pass
    return out
def pct(v, q):
    v = sorted(v); return None if not v else v[min(len(v) - 1, int(q * len(v)))]
def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 1.0)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))
def cp_upper(k, n, a=0.05):
    from math import comb
    if n == 0 or k >= n: return 1.0
    cdf = lambda p: sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
    lo, hi = k / n, 1.0
    for _ in range(60):
        m = (lo + hi) / 2
        if cdf(m) > a: lo = m
        else: hi = m
    return hi
def fisher1(a, b, c, d):
    """one-sided Fisher p that group 1 (a of a+b) has the higher rate than group 2 (c of c+d)"""
    from math import comb
    r1, r2, c1, n = a + b, c + d, a + c, a + b + c + d
    pr = lambda x: comb(r1, x) * comb(r2, c1 - x) / comb(n, c1)
    return sum(pr(x) for x in range(a, min(r1, c1) + 1))
