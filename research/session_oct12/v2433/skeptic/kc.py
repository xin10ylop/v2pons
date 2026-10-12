"""Skeptic helpers: own code, paced public RPC via research/session_oct12/c1/rpc.py (read methods only)."""
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
RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
T_TR = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
V2433 = 2433328500000000000
SQ2433 = 1604517591721945638372359205383840
L2433 = 49279426163460954002188
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x, bits=256): return x - (1 << bits) if x >= (1 << (bits - 1)) else x
def p(n): return os.path.join(HERE, n)
def ts(t): return time.strftime("%m-%d %H:%M:%S", time.gmtime(t))
def topaddr(t): return "0x" + t[-40:]
def cached_logs(name, flt, a, b, step=20000):
    """Scan logs in chunks, cache chunk results in name (jsonl rows {a,b,logs})."""
    fn = p(name); done = {}
    if os.path.exists(fn):
        for l in open(fn):
            r = json.loads(l); done[(r["a"], r["b"])] = r["logs"]
    out = []
    x = a
    while x <= b:
        y = min(b, x + step - 1)
        if (x, y) not in done:
            lg = R.logs(flt, x, y)
            with open(fn, "a") as f: f.write(json.dumps({"a": x, "b": y, "logs": lg}) + "\n")
            done[(x, y)] = lg
        out += done[(x, y)]
        x = y + 1
    return out
def block_ts_map(name, blocks):
    fn = p(name); m = {}
    if os.path.exists(fn):
        for l in open(fn):
            r = json.loads(l); m[r["b"]] = r["t"]
    need = sorted(set(b for b in blocks if b not in m))
    for i in range(0, len(need), 20):
        ch = need[i:i + 20]
        res = R.batch("eth_getBlockByNumber", [[hex(b), False] for b in ch])
        with open(fn, "a") as f:
            for b, r in zip(ch, res):
                m[b] = int(r["timestamp"], 16); f.write(json.dumps({"b": b, "t": m[b]}) + "\n")
    return m
def txs(name, hashes):
    fn = p(name); m = {}
    if os.path.exists(fn):
        for l in open(fn):
            r = json.loads(l); m[r["hash"]] = r
    need = sorted(set(h for h in hashes if h not in m))
    for i in range(0, len(need), 20):
        ch = need[i:i + 20]
        res = R.batch("eth_getTransactionByHash", [[h] for h in ch])
        with open(fn, "a") as f:
            for h, r in zip(ch, res):
                if r is None: continue
                row = {"hash": h, "from": r["from"].lower(), "to": (r.get("to") or "").lower(), "value": int(r["value"], 16), "input": r["input"], "nonce": int(r["nonce"], 16), "gas": int(r["gas"], 16), "block": int(r["blockNumber"], 16)}
                m[h] = row; f.write(json.dumps(row) + "\n")
    return m
