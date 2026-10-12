"""v30/timing helpers: paced public RPC via research/session_oct12/c1/rpc.py (read methods only, one POST >= 0.5 s apart).
Caches are *_cache.jsonl (git-ignored)."""
import sys, os, json, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct12/c1"); sys.dont_write_bytecode = True
import rpc as R
from eth_utils import keccak
HERE = os.path.dirname(os.path.abspath(__file__))
R.LOG = os.path.join(HERE, "rpc_log.jsonl")
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
BOT = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
OURWALLET = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
SENTINEL = "0xe71a69f4"
SQ30 = 679394651928963067279918579724198
SQ50 = 526364174002223567019744861584709
DUST = 3 * 10 ** 13  # 0.00003 ETH
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
T_TR = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
Z = "0x" + "0" * 40
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x, bits=256): return x - (1 << bits) if x >= (1 << (bits - 1)) else x
def p(n): return os.path.join(HERE, n)
def ts(t): return time.strftime("%m-%d %H:%M:%S", time.gmtime(t))
def hh(t): return time.strftime("%Hh", time.gmtime(t))
def topaddr(t): return "0x" + t[-40:]
import glob as _glob
def parts(name):
    """a cache file and its split parts (<base>_pNN_cache.jsonl), so no file exceeds 2 MB"""
    base = p(name)[:-len("_cache.jsonl")]
    return [f for f in [p(name)] if os.path.exists(f)] + sorted(_glob.glob(base + "_p[0-9][0-9]_cache.jsonl"))
def lines(name):
    for f in parts(name):
        for l in open(f): yield l
def split_big(limit=1900000):
    """split every *_cache.jsonl over limit into <base>_pNN_cache.jsonl parts (line boundaries)"""
    for f in sorted(_glob.glob(p("*_cache.jsonl"))):
        if os.path.getsize(f) <= limit: continue
        base = f[:-len("_cache.jsonl")]; k = len(_glob.glob(base + "_p[0-9][0-9]_cache.jsonl")); buf = []; size = 0
        for l in open(f):
            if size + len(l) > limit and buf:
                open("%s_p%02d_cache.jsonl" % (base, k), "w").write("".join(buf)); k += 1; buf = []; size = 0
            buf.append(l); size += len(l)
        if buf: open("%s_p%02d_cache.jsonl" % (base, k), "w").write("".join(buf))
        os.remove(f)
def q(v, x):
    v = sorted(v); return v[min(len(v) - 1, int(x * len(v)))] if v else None
def cached_logs(name, flt, a, b, step=20000):
    fn = p(name); done = {}
    for l in lines(name):
        r = json.loads(l); done[(r["a"], r["b"])] = r["logs"]
    out = []; x = a
    while x <= b:
        y = min(b, x + step - 1)
        if (x, y) not in done:
            lg = R.logs(flt, x, y)
            with open(fn, "a") as f: f.write(json.dumps({"a": x, "b": y, "logs": lg}) + "\n")
            done[(x, y)] = lg
        out += done[(x, y)]; x = y + 1
    return out
def block_ts_map(name, blocks):
    fn = p(name); m = {}
    for l in lines(name):
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
    for l in lines(name):
        r = json.loads(l); m[r["hash"]] = r
    need = sorted(set(h for h in hashes if h not in m))
    for i in range(0, len(need), 20):
        ch = need[i:i + 20]
        res = R.batch("eth_getTransactionByHash", [[h] for h in ch])
        with open(fn, "a") as f:
            for h, r in zip(ch, res):
                if r is None: continue
                row = {"hash": h, "from": r["from"].lower(), "to": (r.get("to") or "").lower(), "value": int(r["value"], 16), "input": r["input"][:202] if len(r["input"]) > 4000 else r["input"],
                       "clen": (len(r["input"]) - 2) // 2, "nonce": int(r["nonce"], 16), "gas": int(r["gas"], 16), "block": int(r["blockNumber"], 16), "idx": int(r["transactionIndex"], 16)}
                m[h] = row; f.write(json.dumps(row) + "\n")
    return m
def full_blocks(name, blocks):
    """full blocks with txs (input truncated to 202 chars + length), cached as {b, t, txs:[...]}"""
    fn = p(name); m = {}
    for l in lines(name):
        r = json.loads(l); m[r["b"]] = r
    need = sorted(set(b for b in blocks if b not in m))
    for i in range(0, len(need), 10):
        ch = need[i:i + 10]
        res = R.batch("eth_getBlockByNumber", [[hex(b), True] for b in ch], n=10)
        with open(fn, "a") as f:
            for b, r in zip(ch, res):
                tl = [{"h": x["hash"], "f": x["from"].lower(), "to": (x.get("to") or "").lower(), "v": int(x["value"], 16), "in": x["input"][:202], "cl": (len(x["input"]) - 2) // 2,
                       "n": int(x["nonce"], 16), "i": int(x["transactionIndex"], 16)} for x in r["transactions"]]
                row = {"b": b, "t": int(r["timestamp"], 16), "txs": tl}
                m[b] = row; f.write(json.dumps(row) + "\n")
    return m
