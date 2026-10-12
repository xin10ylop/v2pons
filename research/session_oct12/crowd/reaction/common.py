"""shared helpers for the v3crowd reaction study (session_oct12/crowd/reaction). Read-only; polite RPC via ./rpc.py (one POST >= 0.5 s apart)."""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.dont_write_bytecode = True
sys.path.append("/home/user/v2pons/research/session_oct11/lines/analysis/W")
J = lambda n: os.path.join(HERE, n)
from eth_utils import keccak
tp = lambda s: "0x" + keccak(text=s).hex()
FACT = "0x1f7d7550b1b028f7571e69a784071f0205fd2efa"; NPM = "0x73991a25c818bf1f1128deaab1492d45638de0d3"
WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"; UR = "0x8876789976decbfcbbbe364623c63652db8c0904"; SR02 = "0xcaf681a66d020601342297493863e78c959e5cb2"
T_PC = tp("PoolCreated(address,address,uint24,int24,address)"); T_SW = tp("Swap(address,address,int256,int256,uint160,uint128,int24)")
T_MI = tp("Mint(address,address,int24,int24,uint128,uint256,uint256)"); T_BU = tp("Burn(address,int24,int24,uint128,uint256,uint256)")
T_CO = tp("Collect(address,address,int24,int24,uint128,uint128)")
CROWD_SHAPES = {("3593564c", 484), ("a0193551", 452), ("49f74a5d", 452)}
def S(x): x = int(x, 16); return x - (1 << 256) if x >> 255 else x
def Wd(d, i): return d[2 + 64 * i: 2 + 64 * (i + 1)]
def utc(ts): return time.strftime("%m-%d %H:%M:%S", time.gmtime(ts))
def jl(p): return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
def pct(v, q):
    v = sorted(v)
    return None if not v else v[min(len(v) - 1, int(q * len(v)))]
def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 1.0)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))
def cp_upper(k, n, a=0.05):
    from math import comb
    if k >= n: return 1.0
    cdf = lambda p: sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
    lo, hi = k / n, 1.0
    for _ in range(60):
        m = (lo + hi) / 2
        if cdf(m) > a: lo = m
        else: hi = m
    return hi
def fisher(a, b, c, d):
    """2x2 [[a,b],[c,d]] -> (one-sided p for a large, two-sided p)"""
    from math import comb
    r1, r2, c1, n = a + b, c + d, a + c, a + b + c + d
    pr = lambda x: comb(r1, x) * comb(r2, c1 - x) / comb(n, c1)
    lo, hi = max(0, c1 - r2), min(r1, c1)
    p0 = pr(a); one = sum(pr(x) for x in range(a, hi + 1)); two = sum(pr(x) for x in range(lo, hi + 1) if pr(x) <= p0 * (1 + 1e-9))
    return one, min(1.0, two)
def mwu(x, y):
    """Mann-Whitney U, normal approximation with ties; -> (U, two-sided p)"""
    import math
    allv = sorted([(v, 0) for v in x] + [(v, 1) for v in y]); n1, n2 = len(x), len(y)
    if not n1 or not n2: return None, None
    ranks = {}; i = 0; r1 = 0.0; tie = 0.0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]: j += 1
        rk = (i + j + 1) / 2; t = j - i; tie += t ** 3 - t
        for k in range(i, j):
            if allv[k][1] == 0: r1 += rk
        i = j
    U = r1 - n1 * (n1 + 1) / 2; mu = n1 * n2 / 2; N = n1 + n2
    sd = math.sqrt(n1 * n2 / 12 * ((N + 1) - tie / (N * (N - 1))))
    if sd == 0: return U, 1.0
    z = (U - mu) / sd
    return U, math.erfc(abs(z) / math.sqrt(2))
def boot_mean_ci(v, n=4000, seed=1):
    import random
    if not v: return (None, None)
    rnd = random.Random(seed); m = []
    for _ in range(n):
        s = [v[rnd.randrange(len(v))] for _ in v]; m.append(sum(s) / len(s))
    m.sort(); return m[int(0.025 * n)], m[int(0.975 * n)]
