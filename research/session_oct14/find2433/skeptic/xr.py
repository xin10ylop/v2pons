"""Skeptic's read-only multi-chain JSON-RPC: public endpoints only (no Dwellir, no key), read methods only.
Robinhood Chain posts are paced >= 0.5 s under a cross-process file lock."""
import json, time, os, ssl, fcntl, urllib.request, urllib.error
EP = {"rh": "https://rpc.mainnet.chain.robinhood.com",
      "eth": "https://ethereum-rpc.publicnode.com", "base": "https://base-rpc.publicnode.com",
      "uni": "https://unichain-rpc.publicnode.com", "arb": "https://arbitrum-one-rpc.publicnode.com",
      "bsc": "https://bsc-rpc.publicnode.com", "bsc_h": "https://rpc-bsc.48.club", "bsc_d": "https://bsc.drpc.org",
      "op": "https://optimism-rpc.publicnode.com", "polygon": "https://polygon-bor-rpc.publicnode.com",
      "avax": "https://avalanche-c-chain-rpc.publicnode.com", "hyper": "https://rpc.hyperliquid.xyz/evm",
      "sonic": "https://sonic-rpc.publicnode.com", "linea": "https://linea-rpc.publicnode.com", "blast": "https://blast-rpc.publicnode.com",
      "ink": "https://rpc-gel.inkonchain.com", "soneium": "https://soneium-rpc.publicnode.com", "world": "https://worldchain-mainnet.g.alchemy.com/public",
      "monad": "https://rpc.monad.xyz", "plasma": "https://rpc.plasma.to", "megaeth": "https://mainnet.megaeth.com/rpc",
      "eth_h": "https://eth.drpc.org", "base_h": "https://base.drpc.org"}
PACE = {"rh": 0.5, "bsc_h": 0.35, "bsc_d": 1.0, "eth_h": 0.5, "base_h": 0.5}
ALLOWED = {"eth_call", "eth_getLogs", "eth_getTransactionByHash", "eth_getTransactionReceipt", "eth_getCode", "eth_getBlockByNumber",
           "eth_blockNumber", "eth_chainId", "eth_getBalance", "eth_getTransactionCount", "eth_getStorageAt", "eth_getBlockReceipts"}
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt") if os.path.exists("/root/.ccr/ca-bundle.crt") else None
HERE = os.path.dirname(os.path.abspath(__file__))
_last = {}; STATS = {}
LOCK = os.path.join(HERE, ".rh_pace.lock")


def _wait_rh():
    """cross-process: at least PACE['rh'] s between Robinhood posts (the lock file holds the last post time)"""
    with open(LOCK, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0); s = f.read().strip()
        last = float(s) if s else 0.0
        dt = time.time() - last
        if dt < PACE["rh"]: time.sleep(PACE["rh"] - dt)
        f.seek(0); f.truncate(); f.write(str(time.time())); f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)


def _post(ch, body):
    url = EP[ch]; pace = PACE.get(ch, 0.2); err = None
    for i in range(8):
        if ch == "rh":
            _wait_rh()
        else:
            dt = time.time() - _last.get(ch, 0)
            if dt < pace: time.sleep(pace - dt)
            _last[ch] = time.time()
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(), H), timeout=90, context=CTX))
            STATS[ch] = STATS.get(ch, 0) + 1
            return d
        except urllib.error.HTTPError as e:
            err = e
            if e.code in (429, 500, 502, 503, 504): time.sleep(2 * (i + 1)); continue
            raise
        except Exception as e:
            err = e; time.sleep(2 * (i + 1))
    raise RuntimeError(f"rpc failed {ch}: {err}")


def call(ch, method, params):
    assert method in ALLOWED, method
    d = _post(ch, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    if "error" in d: raise RuntimeError(json.dumps(d["error"])[:300])
    return d["result"]


def batch(ch, method, plist, n=20):
    assert method in ALLOWED, method
    out = []
    for i in range(0, len(plist), n):
        chunk = plist[i:i + n]
        for attempt in range(5):
            d = _post(ch, [{"jsonrpc": "2.0", "id": j, "method": method, "params": p} for j, p in enumerate(chunk)])
            if isinstance(d, list) and all("result" in x for x in d): break
            time.sleep(2 * (attempt + 1))
        if isinstance(d, dict): raise RuntimeError(json.dumps(d)[:300])
        d = sorted(d, key=lambda x: x["id"]); out += [x.get("result") for x in d]
    return out


def logs(ch, flt, a, b, maxspan=None):
    if maxspan and b - a + 1 > maxspan:
        out = []
        for s in range(a, b + 1, maxspan): out += logs(ch, flt, s, min(s + maxspan - 1, b))
        return out
    try: return call(ch, "eth_getLogs", [dict(flt, fromBlock=hex(a), toBlock=hex(b))])
    except RuntimeError:
        if b <= a: raise
        m = (a + b) // 2; return logs(ch, flt, a, m) + logs(ch, flt, m + 1, b)


def head(ch):
    b = call(ch, "eth_getBlockByNumber", ["latest", False]); return int(b["number"], 16), int(b["timestamp"], 16)


def ts_of(ch, n): return int(call(ch, "eth_getBlockByNumber", [hex(n), False])["timestamp"], 16)


def W(data, i):
    h = data[2:] if data.startswith("0x") else data
    return int(h[64 * i:64 * (i + 1)], 16)


def sgn(x, bits=256): return x - (1 << bits) if x >> (bits - 1) else x
