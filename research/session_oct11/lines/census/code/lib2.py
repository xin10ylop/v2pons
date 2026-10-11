"""scanner2 census: RPC + cache helpers (gzip, per-item retry, gentle pacing, append-only JSONL caches)."""
import sys, os, json, time, gzip, urllib.request, urllib.error
from eth_utils import keccak  # noqa: F401
RPC = "https://rpc.mainnet.chain.robinhood.com"
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128", "Accept-Encoding": "gzip"}
CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census"
CACHE = os.path.join(CEN, "cache"); os.makedirs(CACHE, exist_ok=True)
OLD = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census/cache"   # first census's raw cache
STATS = {"posts": 0, "items": 0, "429": 0, "errs": 0, "bytes_wire": 0, "bytes": 0, "item_errs": 0}
MIN_GAP = float(os.environ.get("MIN_GAP", "0.35"))   # seconds between POSTs (pacing)
_last = [0.0]
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x): return x - (1 << 256) if x >= (1 << 255) else x


def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)


def post(body, tries=16):
    last = None
    for i in range(tries):
        gap = time.time() - _last[0]
        if gap < MIN_GAP: time.sleep(MIN_GAP - gap)
        _last[0] = time.time()
        try:
            STATS["posts"] += 1
            r = urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(body).encode(), H), timeout=120)
            raw = r.read(); data = gzip.decompress(raw) if r.headers.get("Content-Encoding") == "gzip" else raw
            STATS["bytes_wire"] += len(raw); STATS["bytes"] += len(data)
            out = json.loads(data)
            if isinstance(body, list) and not isinstance(out, list):
                last = out; time.sleep(3 + 2 * i); continue
            return out
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429: STATS["429"] += 1; time.sleep(min(60, 4 * (i + 1)))
            else: STATS["errs"] += 1; time.sleep(2 + i)
        except Exception as e:
            last = e; STATS["errs"] += 1; time.sleep(2 + 2 * i)
    raise RuntimeError(f"rpc failed: {str(last)[:300]}")


def rpc(m, p):
    r = post({"jsonrpc": "2.0", "id": 1, "method": m, "params": p})
    if "error" in r: raise RuntimeError(str(r["error"])[:300])
    return r["result"]


def batch(calls, size=50, item_tries=6):
    """[(method, params)] -> [result or None]; items answered with an error are retried."""
    out = [None] * len(calls); todo = list(range(len(calls)))
    for attempt in range(item_tries):
        nxt = []
        for i in range(0, len(todo), size):
            ch = todo[i:i + size]
            r = post([{"jsonrpc": "2.0", "id": j, "method": calls[j][0], "params": calls[j][1]} for j in ch])
            STATS["items"] += len(ch)
            got = {x.get("id"): x for x in r if isinstance(x, dict)}
            for j in ch:
                x = got.get(j)
                if x is None or "error" in x: nxt.append(j); STATS["item_errs"] += 1
                else: out[j] = x.get("result")
        if not nxt: break
        todo = nxt; time.sleep(3 + 3 * attempt)
    return out


def logs(flt, a, b, maxspan=None):
    if maxspan and b - a + 1 > maxspan:
        res = []; x = a
        while x <= b:
            y = min(b, x + maxspan - 1); res += logs(flt, x, y); x = y + 1
        return res
    try: return rpc("eth_getLogs", [dict(flt, fromBlock=hex(a), toBlock=hex(b))])
    except RuntimeError as e:
        if b <= a or "invalid argument" in str(e): raise
        m = (a + b) // 2; return logs(flt, a, m) + logs(flt, m + 1, b)


def block_ts(n): return int(rpc("eth_getBlockByNumber", [hex(n), False])["timestamp"], 16)


def block_at(ts, hi=None):
    lo = 1; hi = hi or int(rpc("eth_blockNumber", []), 16)
    while lo < hi:
        mid = (lo + hi) // 2
        if block_ts(mid) < ts: lo = mid + 1
        else: hi = mid
    return lo


def jl_read(name, d=None):
    p = os.path.join(d or CACHE, name); out = []
    if not os.path.exists(p): return out
    with open(p) as f:
        for line in f:
            try: out.append(json.loads(line))
            except Exception: pass
    return out


def jl_iter(name, d=None):
    p = os.path.join(d or CACHE, name)
    if not os.path.exists(p): return
    with open(p) as f:
        for line in f:
            try: yield json.loads(line)
            except Exception: pass


def jl_append(name, objs):
    with open(os.path.join(CACHE, name), "a") as f:
        for o in objs: f.write(json.dumps(o, separators=(",", ":")) + "\n")
        f.flush()


def jget(name, default=None):
    try: return json.load(open(os.path.join(CACHE, name)))
    except Exception: return default


def jput(name, v):
    p = os.path.join(CACHE, name); json.dump(v, open(p + ".tmp", "w")); os.replace(p + ".tmp", p)


def timing(step, secs, extra=None):
    t = jget("timing.json", {}); t.setdefault(step, []).append({"secs": round(secs, 1), "at": time.strftime("%H:%M:%S"), **dict(STATS), **(extra or {})}); jput("timing.json", t)


# ---- bytecode helpers
def skeleton(code_hex):
    """opcode sequence with every PUSH operand dropped and the trailing CBOR metadata stripped -> keccak hex (None for empty code).
    Robust to immutables (PUSH32 placeholders), hardcoded constants/strings and the metadata hash."""
    b = bytes.fromhex(code_hex[2:] if code_hex.startswith("0x") else code_hex)
    if not b: return None
    if len(b) > 2:
        ml = int.from_bytes(b[-2:], "big")
        if 0 < ml < len(b) - 2 and b[-2 - ml] in (0xa1, 0xa2, 0xa3): b = b[:-2 - ml]
    out = bytearray(); i = 0; n = len(b)
    while i < n:
        op = b[i]; out.append(op)
        if 0x60 <= op <= 0x7f: i += op - 0x5f
        i += 1
    return keccak(bytes(out)).hex()


# EVM snippet for eth_call with a state override: calldata = N x 32-byte addresses -> N x (extcodehash, extcodesize)
HASHER = "0x60005b36811015602257803580" + "3f8260020252" + "3b8160020260200152" + "602001600256" + "5b60020260" + "00f3"
HASHER_ADDR = "0x00000000000000000000000000000000000c0de1"


def codehashes(addrs, per_call=800):
    """addr -> (codehash hex or None, size) at latest, via one eth_call per per_call addresses (state-override code)."""
    out = {}
    for i in range(0, len(addrs), per_call):
        ch = addrs[i:i + per_call]
        data = "0x" + "".join("0" * 24 + a[2:] for a in ch)
        r = rpc("eth_call", [{"to": HASHER_ADDR, "data": data, "gas": hex(30_000_000)}, "latest", {HASHER_ADDR: {"code": HASHER}}])
        for j, a in enumerate(ch):
            h = r[2 + 128 * j: 2 + 128 * j + 64]; sz = int(r[2 + 128 * j + 64: 2 + 128 * (j + 1)], 16)
            out[a] = (None if sz == 0 else h, sz)
    return out
