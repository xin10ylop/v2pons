"""T3 skeptic 2 for candidate 3 (precursor): read-only JSON-RPC to the public Robinhood Chain node (no key), with 429 back-off, a minimum gap between POSTs,
and append-only disk caches for full blocks, block receipts and transactions (cache/)."""
import json, time, os, urllib.request, urllib.error
from eth_utils import keccak
RPC = "https://rpc.mainnet.chain.robinhood.com"; H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}
HERE = os.path.dirname(os.path.abspath(__file__)); CACHE = os.path.join(HERE, "cache"); os.makedirs(CACHE, exist_ok=True)
ALLOWED = {"eth_getLogs", "eth_getTransactionByHash", "eth_getBlockByNumber", "eth_blockNumber", "eth_getBlockReceipts", "eth_getTransactionCount", "eth_getBalance"}
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
BOT = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"; UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
PERMIT2 = "0x000000000022d473030f116ddee9f6b43ac78ba3"; SENTINEL = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
OURS = "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"; RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
SQRT30 = 679394651928963067279918579724198
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
T_TRANSFER = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
T_APPROVAL = "0x" + keccak(text="Approval(address,address,uint256)").hex()
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x): return x - (1 << 256) if x >= (1 << 255) else x
GAP = float(os.environ.get("RPC_GAP", "0.6")); _last = [0.0]
LOG = open(os.path.join(HERE, "rpc_log.jsonl"), "a")


def post(body, what):
    for i in range(40):
        dt = time.time() - _last[0]
        if dt < GAP: time.sleep(GAP - dt)
        _last[0] = time.time(); t = time.time()
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(body).encode(), H), timeout=120))
            LOG.write(json.dumps({"t": round(t, 2), "what": what, "ok": 1, "dt": round(time.time() - t, 2)}) + "\n"); LOG.flush()
            return r
        except urllib.error.HTTPError as e:
            LOG.write(json.dumps({"t": round(t, 2), "what": what, "http": e.code}) + "\n"); LOG.flush()
            time.sleep(min(45, 3 * (i + 1)) if e.code == 429 else 3)
        except Exception as e:
            LOG.write(json.dumps({"t": round(t, 2), "what": what, "err": str(e)[:100]}) + "\n"); LOG.flush()
            time.sleep(3 + 2 * i)
    raise RuntimeError("rpc failed: " + what)


def rpc(m, p):
    assert m in ALLOWED
    r = post({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}, m)
    if "error" in r: raise RuntimeError(str(r["error"])[:200])
    return r["result"]


def batch(calls, size=20):
    out = []
    for m, _ in calls: assert m in ALLOWED
    for i in range(0, len(calls), size):
        ch = calls[i:i + size]; res = None
        for k in range(8):
            r = post([{"jsonrpc": "2.0", "id": j, "method": m, "params": p} for j, (m, p) in enumerate(ch)], f"batch{len(ch)}:{ch[0][0]}")
            if isinstance(r, list) and len(r) == len(ch) and all("result" in x for x in r):
                res = [x["result"] for x in sorted(r, key=lambda x: x["id"])]; break
            time.sleep(4 * (k + 1))
        out += res if res is not None else [None] * len(ch)
    return out


def logs(flt, a, b):
    try: return rpc("eth_getLogs", [dict(flt, fromBlock=hex(a), toBlock=hex(b))])
    except RuntimeError:
        if b <= a: raise
        m = (a + b) // 2; return logs(flt, a, m) + logs(flt, m + 1, b)


class KV:
    """append-only jsonl cache keyed by k (a torn last line is skipped)"""
    def __init__(self, name):
        self.path = os.path.join(CACHE, name + ".jsonl"); self.d = {}
        if os.path.exists(self.path):
            with open(self.path) as f:
                for l in f:
                    try: x = json.loads(l); self.d[x["k"]] = x["v"]
                    except Exception: pass
        self.f = open(self.path, "a")
        if self.f.tell() > 0: self.f.write("\n")
    def put(self, k, v): self.d[k] = v; self.f.write(json.dumps({"k": k, "v": v}) + "\n")
    def flush(self): self.f.flush()
    def close(self): self.f.close()


SLIM_TX = ("hash", "from", "to", "nonce", "value", "input", "blockNumber", "transactionIndex", "type", "gasPrice", "maxPriorityFeePerGas", "maxFeePerGas", "gas")


def slim_block(b):
    return {"number": int(b["number"], 16), "ts": int(b["timestamp"], 16), "txs": [{k: t.get(k) for k in SLIM_TX} for t in b["transactions"]]}


def slim_receipts(rs):
    return [{"tx": r["transactionHash"], "status": r.get("status"), "gasUsed": r.get("gasUsed"), "from": r.get("from"), "to": r.get("to"),
             "logs": [{"a": l["address"].lower(), "t": l["topics"], "d": l["data"], "li": int(l["logIndex"], 16)} for l in r.get("logs", [])]} for r in rs]


def get_blocks(nums, kv_b, kv_r, receipts=True, size=50):
    need = [n for n in dict.fromkeys(nums) if str(n) not in kv_b.d]
    for i in range(0, len(need), 200):
        ch = need[i:i + 200]
        res = batch([("eth_getBlockByNumber", [hex(n), True]) for n in ch], 25)
        for n, b in zip(ch, res):
            if b: kv_b.put(str(n), slim_block(b))
        kv_b.flush()
    if receipts:
        need = [n for n in dict.fromkeys(nums) if str(n) not in kv_r.d]
        for i in range(0, len(need), 200):
            ch = need[i:i + 200]
            res = batch([("eth_getBlockReceipts", [hex(n)]) for n in ch], 10)
            for n, r in zip(ch, res):
                if r is not None: kv_r.put(str(n), slim_receipts(r))
            kv_r.flush()


def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(p * len(v)))] if v else None


def utc(ts): return time.strftime("%m-%d %H:%M:%S", time.gmtime(ts))
