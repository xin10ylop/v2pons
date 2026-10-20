"""Shared helpers for the v2.433 fingerprint study (read-only, public RPC only, paced by research/session_oct12/c1/rpc.py)."""
import sys, os, json, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct12/c1")
import rpc as R
from eth_utils import keccak
HERE = os.path.dirname(os.path.abspath(__file__))
R.LOG = os.path.join(HERE, "rpc_log.jsonl")
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
BOT = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
T_TRANSFER = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
V2433 = 2433328500000000000
SQRTP_2433 = 1604517591721945638372359205383840
LIQ_2433 = 49279426163460954002188
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x, bits=256): return x - (1 << bits) if x >= (1 << (bits - 1)) else x
def p(name): return os.path.join(HERE, name)
def load_jsonl(name):
    fn = p(name)
    if not os.path.exists(fn): return []
    return [json.loads(l) for l in open(fn) if l.strip()]
def append_jsonl(name, rows):
    with open(p(name), "a") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
def hhmm(t): return time.strftime("%m-%d %H:%M:%S", time.gmtime(t))
