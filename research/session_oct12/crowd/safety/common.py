"""shared constants/helpers for the v3crowd safety and execution check (session_oct12/crowd/safety). Read-only; polite RPC via ./rpc.py
(one POST at a time, >= 0.6 s apart, back-off on 429; read methods only)."""
import os, sys, json, time, calendar
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.dont_write_bytecode = True
J = lambda n: os.path.join(HERE, n)
from eth_utils import keccak
tp = lambda s: "0x" + keccak(text=s).hex()
FACT = "0x1f7d7550b1b028f7571e69a784071f0205fd2efa"
NPM = "0x73991a25c818bf1f1128deaab1492d45638de0d3"
WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
ROUTER02 = "0xcaf681a66d020601342297493863e78c959e5cb2"
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
QUOTER2 = "0x33e885ed0ec9bf04ecfb19341582aadcb4c8a9e7"
USDG = "0x5fc5360d0400a0fd4f2af552add042d716f1d168"
T_PC = tp("PoolCreated(address,address,uint24,int24,address)")
T_SW = tp("Swap(address,address,int256,int256,uint160,uint128,int24)")
T_MI = tp("Mint(address,address,int24,int24,uint128,uint256,uint256)")
T_BU = tp("Burn(address,int24,int24,uint128,uint256,uint256)")
T_TR = tp("Transfer(address,address,uint256)")
T_OWN = tp("OwnershipTransferred(address,address)")
CROWD_SHAPES = {("3593564c", 484): 9, ("a0193551", 452): 8, ("49f74a5d", 452): 8}
START_TS = calendar.timegm((2026, 10, 10, 0, 0, 0))
def W(d, i): return int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x): return x - (1 << 256) if x >> 255 else x
def utc(ts): return time.strftime("%m-%d %H:%M:%S", time.gmtime(ts))
def jl(p): return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
def word(x): return ("%064x" % (x % (1 << 256))) if isinstance(x, int) else x.lower().replace("0x", "").zfill(64)
def pct(v, q):
    v = sorted(v)
    if not v: return None
    k = (len(v) - 1) * q; f = int(k); c = min(f + 1, len(v) - 1)
    return v[f] + (v[c] - v[f]) * (k - f)
