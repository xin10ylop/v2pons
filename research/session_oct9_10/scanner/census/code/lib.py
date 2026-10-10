"""Shared RPC + cache helpers for the census (robust batch with per-item retry, append-only JSONL caches)."""
import sys, os, json, time, urllib.request, urllib.error
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10"); sys.path.insert(0, "/home/user/v2pons/src")
from chain import RPC, H, PM, T_INIT, T_SWAP, T_ML, W, sgn  # noqa: F401
from eth_utils import keccak  # noqa: F401

CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census"
CACHE = os.path.join(CEN, "cache")
os.makedirs(CACHE, exist_ok=True)
STATS = {"posts": 0, "429": 0, "errs": 0}


def post(body, tries=14):
    last = None
    for i in range(tries):
        try:
            STATS["posts"] += 1
            r = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(body).encode(), H), timeout=120))
            if isinstance(body, list) and not isinstance(r, list):
                last = r; time.sleep(3 + 2 * i); continue          # a whole-batch error object (rate limit): retry
            return r
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429: STATS["429"] += 1; time.sleep(min(60, 3 * (i + 1)))
            else: STATS["errs"] += 1; time.sleep(2 + i)
        except Exception as e:
            last = e; STATS["errs"] += 1; time.sleep(2 + i)
    raise RuntimeError(f"rpc failed: {str(last)[:200]}")


def rpc(m, p):
    r = post({"jsonrpc": "2.0", "id": 1, "method": m, "params": p})
    if "error" in r: raise RuntimeError(str(r["error"])[:300])
    return r["result"]


def batch(calls, size=50, item_tries=6):
    """[(method, params)] -> [result or None]; items answered with an error are retried (rate limits are per item here too)."""
    out = [None] * len(calls); todo = list(range(len(calls)))
    for attempt in range(item_tries):
        nxt = []
        for i in range(0, len(todo), size):
            ch = todo[i:i + size]
            r = post([{"jsonrpc": "2.0", "id": j, "method": calls[j][0], "params": calls[j][1]} for j in ch])
            got = {x.get("id"): x for x in r if isinstance(x, dict)}
            for j in ch:
                x = got.get(j)
                if x is None or "error" in x: nxt.append(j)
                else: out[j] = x.get("result")
        if not nxt: break
        todo = nxt; time.sleep(2 + 2 * attempt)
    return out


def logs(flt, a, b, maxspan=None):
    """eth_getLogs over [a, b], splitting the range on error (range limits, result-size limits)."""
    if maxspan and b - a + 1 > maxspan:
        res = []; x = a
        while x <= b:
            y = min(b, x + maxspan - 1); res += logs(flt, x, y); x = y + 1
        return res
    try: return rpc("eth_getLogs", [dict(flt, fromBlock=hex(a), toBlock=hex(b))])
    except RuntimeError:
        if b <= a: raise
        m = (a + b) // 2; return logs(flt, a, m) + logs(flt, m + 1, b)


def block_ts(n): return int(rpc("eth_getBlockByNumber", [hex(n), False])["timestamp"], 16)


def block_at(ts, hi=None):
    lo = 1; hi = hi or int(rpc("eth_blockNumber", []), 16)
    while lo < hi:
        mid = (lo + hi) // 2
        if block_ts(mid) < ts: lo = mid + 1
        else: hi = mid
    return lo


# ---- append-only JSONL caches (a crash loses at most the line being written)
def jl_read(name):
    p = os.path.join(CACHE, name); out = []
    if not os.path.exists(p): return out
    with open(p) as f:
        for line in f:
            try: out.append(json.loads(line))
            except Exception: pass
    return out


def jl_append(name, objs):
    with open(os.path.join(CACHE, name), "a") as f:
        for o in objs: f.write(json.dumps(o, separators=(",", ":")) + "\n")
        f.flush()


def jget(name, default=None):
    p = os.path.join(CACHE, name)
    try: return json.load(open(p))
    except Exception: return default


def jput(name, v):
    p = os.path.join(CACHE, name); json.dump(v, open(p + ".tmp", "w")); os.replace(p + ".tmp", p)


def s128(x):
    """a 256-bit word holding a signed int128 (sign-extended by the ABI) -> python int"""
    return sgn(x)


def timing(step, secs, extra=None):
    t = jget("timing.json", {}); t[step] = {"secs": round(secs, 1), **(extra or {})}; jput("timing.json", t)
