"""Shared constants/helpers for the v2.433 wallets-and-money study (session_oct12/v2433/wallets). Read-only; paced RPC via ./rpc.py."""
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
V2433 = 2433328500000000000
SQRTP_2433 = 1604517591721945638372359205383840; LIQ_2433 = 49279426163460954002188
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
T_TRANSFER = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x): return x - (1 << 256) if x >= (1 << 255) else x
def utc(ts): return time.strftime("%m-%d %H:%M:%S", time.gmtime(ts))
def pad(a): return "0x" + "0" * 24 + a.lower()[2:]
def jl(p): return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
def head():
    h = int(rpc.call("eth_blockNumber", []), 16)
    return h, int(rpc.call("eth_getBlockByNumber", [hex(h), False])["timestamp"], 16)
def ts_of(b): return int(rpc.call("eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)
def block_at(t, hint_head=None):
    h, th = hint_head or head()
    lo, hi = max(1, h - int((th - t) * 12) - 50000), h
    while lo < hi:
        m = (lo + hi) // 2
        if ts_of(m) < t: lo = m + 1
        else: hi = m
    return lo
def pct(v, q):
    v = sorted(v)
    return None if not v else v[min(len(v) - 1, int(q * len(v)))]
# block cache: full blocks (with transactions) as compact rows, one JSON line per block
BLK = J("blk_cache.jsonl")
_blk = {}
def _load_blk():
    if _blk or not os.path.exists(BLK): return
    for l in open(BLK):
        try: r = json.loads(l); _blk[r["n"]] = r
        except Exception: pass
def compact_block(b):
    return {"n": int(b["number"], 16), "ts": int(b["timestamp"], 16),
            "txs": [{"h": t["hash"], "f": t["from"].lower(), "to": (t.get("to") or "").lower(), "v": str(int(t["value"], 16)), "nonce": int(t["nonce"], 16),
                     "sel": t["input"][:10], "len": (len(t["input"]) - 2) // 2, "type": t.get("type"),
                     "inp": t["input"] if (len(t["input"]) <= 4000) else t["input"][:4000]} for t in b["transactions"]]}
def get_blocks(nums, per=25):
    _load_blk()
    need = sorted(set(n for n in nums if n not in _blk))
    if need:
        with open(BLK, "a") as f:
            for i in range(0, len(need), per):
                ch = need[i:i + per]
                res = rpc.batch("eth_getBlockByNumber", [[hex(n), True] for n in ch], n=per)
                for n, b in zip(ch, res):
                    if b is None: continue
                    r = compact_block(b); _blk[n] = r; f.write(json.dumps(r) + "\n")
    return {n: _blk[n] for n in nums if n in _blk}
