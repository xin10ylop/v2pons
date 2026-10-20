"""Shared helpers for the trail study (session_oct14/find2433/trail). Read-only; paced public RPC via ./rpc.py (>= 0.5 s between posts)."""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.dont_write_bytecode = True
J = lambda n: os.path.join(HERE, n)
from eth_utils import keccak
import rpc
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
BOT = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
DECOY_R = "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc"
FRONT_R2 = "0xfd1b271f235e5230eaee9d914ccb1af495bfb758"
RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
SENT = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
HUB = "0x6c3bd8f6fbca130f95305e9fa5a37d1dbf31622d"
ZERO = "0x0000000000000000000000000000000000000000"
V2433 = 2433328500000000000
BOT_CODE_HASH = "bd31d4da7db89e01a9bb257fb9840da42b80df746dd53b9e7bf6a245d2cf8968"
SQRTP_2433 = 1604517591721945638372359205383840; LIQ_2433 = 49279426163460954002188
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
T_TRANSFER = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x): return x - (1 << 256) if x >= (1 << 255) else x
def utc(ts): return time.strftime("%m-%d %H:%M:%S", time.gmtime(ts))
def pad(a): return "0x" + "0" * 24 + a.lower()[2:]
def unpad(t): return "0x" + t[-40:]
def jl(p): 
    out = []
    if os.path.exists(p):
        for l in open(p):
            try: out.append(json.loads(l))
            except Exception: pass
    return out
def head():
    h = int(rpc.call("eth_blockNumber", []), 16)
    return h, int(rpc.call("eth_getBlockByNumber", [hex(h), False])["timestamp"], 16)
def ts_of(b): return int(rpc.call("eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)
def pct(v, q):
    v = sorted(v)
    return None if not v else v[min(len(v) - 1, int(q * len(v)))]
def topic_logs(topics, a, b, address=None, step=30000):
    """getLogs over [a, b] in chunks (30k blocks without an address, 100k with one)"""
    out = []
    step = 100000 if address else step
    for s in range(a, b + 1, step):
        e = min(b, s + step - 1)
        flt = {"topics": topics}
        if address: flt["address"] = address
        out += rpc.logs(flt, s, e)
    return out
