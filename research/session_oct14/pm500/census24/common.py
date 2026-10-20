"""Shared constants and helpers for the pm500 census (read-only, public RPC via rpc.py)."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rpc
from eth_utils import keccak
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
T_TRANSFER = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
ZERO32 = "0x" + "0" * 64
def W(d, i): return int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x, bits=256): return x - (1 << bits) if x >= (1 << (bits - 1)) else x
def jload(p):
    with open(os.path.join(HERE, p)) as f: return json.load(f)
def jdump(o, p):
    with open(os.path.join(HERE, p), "w") as f: json.dump(o, f, separators=(",", ":"))
def jl_load(p):
    out = []
    fp = os.path.join(HERE, p)
    if not os.path.exists(fp): return out
    with open(fp) as f:
        for line in f:
            if line.strip(): out.append(json.loads(line))
    return out
def jl_append(rows, p):
    with open(os.path.join(HERE, p), "a") as f:
        for r in rows: f.write(json.dumps(r, separators=(",", ":")) + "\n")
def swap_fields(l):
    d = l["data"]
    return dict(a0=sgn(W(d, 0)), a1=sgn(W(d, 1)), sqrt=W(d, 2), liq=W(d, 3), tick=sgn(W(d, 4)), fee=W(d, 5))
def ml_fields(l):
    d = l["data"]
    return dict(tl=sgn(W(d, 0)), tu=sgn(W(d, 1)), dl=sgn(W(d, 2)), salt=d[2 + 64 * 3: 2 + 64 * 4])
import glob as _glob
def load_events():
    out = []
    for fp in sorted(_glob.glob(os.path.join(HERE, "s02_events_*_cache.jsonl"))):
        out += [r for r in jl_load(os.path.basename(fp)) if "pid" in r]
    return out
def load_txs():
    out = {}
    for fp in sorted(_glob.glob(os.path.join(HERE, "s03_txs_*_cache.jsonl"))):
        for r in jl_load(os.path.basename(fp)): out[r["h"]] = r
    return out
def load_pools():
    out = []
    for fp in sorted(_glob.glob(os.path.join(HERE, "s04_pools_*_cache.jsonl"))): out += jl_load(os.path.basename(fp))
    return sorted(out, key=lambda p: p["L"])
