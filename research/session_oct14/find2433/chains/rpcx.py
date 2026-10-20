"""Read-only multi-chain JSON-RPC over public endpoints only (no Dwellir, no keys). Paced per endpoint; read methods only."""
import json, time, os, ssl, urllib.request, urllib.error
EP = {"rh": "https://rpc.mainnet.chain.robinhood.com",
      "eth": "https://ethereum-rpc.publicnode.com", "base": "https://base-rpc.publicnode.com",
      "uni": "https://unichain-rpc.publicnode.com", "arb": "https://arbitrum-one-rpc.publicnode.com",
      "bsc": "https://bsc-rpc.publicnode.com",
      # history-capable free public endpoints (no key): publicnode serves only the last ~10,000 blocks of logs
      "eth_h": "https://mainnet.gateway.tenderly.co", "eth_d": "https://eth.drpc.org", "eth_m": "https://rpc.mevblocker.io",
      "base_h": "https://base.gateway.tenderly.co", "base_d": "https://base.drpc.org",
      "uni_h": "https://mainnet.unichain.org", "uni_d": "https://unichain.drpc.org", "uni_t": "https://unichain.gateway.tenderly.co",
      "arb_h": "https://arb1.arbitrum.io/rpc", "arb_d": "https://arbitrum.drpc.org", "arb_t": "https://arbitrum.gateway.tenderly.co", "bsc_h": "https://rpc-bsc.48.club", "bsc_d": "https://bsc.drpc.org"}
PACE = {"rh": 0.5, "bsc_h": 0.35, "bsc_d": 1.0, "eth_d": 0.4, "base_d": 0.4, "uni_d": 0.4, "arb_d": 0.4}
ALLOWED = {"eth_call", "eth_getLogs", "eth_getTransactionByHash", "eth_getTransactionReceipt", "eth_getCode", "eth_getBlockByNumber",
           "eth_blockNumber", "eth_chainId", "eth_getBalance", "eth_getTransactionCount", "eth_getStorageAt"}
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt") if os.path.exists("/root/.ccr/ca-bundle.crt") else None
_last = {}; STATS = {}
HERE = os.path.dirname(os.path.abspath(__file__)); LOG = os.path.join(HERE, "rpc_log.jsonl")
def _post(ch, body):
    url = EP[ch]; pace = PACE.get(ch, 0.25); err = None
    for i in range(8):
        dt = time.time() - _last.get(ch, 0)
        if dt < pace: time.sleep(pace - dt)
        _last[ch] = time.time()
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(), H), timeout=90, context=CTX))
            STATS[ch] = STATS.get(ch, 0) + 1
            return d
        except urllib.error.HTTPError as e:
            err = e
            if e.code in (429, 502, 503, 504): time.sleep(2 * (i + 1)); continue
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
        d = _post(ch, [{"jsonrpc": "2.0", "id": j, "method": method, "params": p} for j, p in enumerate(chunk)])
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
BT = {"rh": 0.1, "eth": 12.0, "base": 2.0, "uni": 1.0, "arb": 0.25, "bsc": 0.45}
for _k in list(EP):
    if "_" in _k: BT[_k] = BT[_k.split("_")[0]]
def block_at(ch, t):
    h, th = head(ch)
    lo = max(1, h - int((th - t) / BT[ch] * 1.5) - 1000); hi = h
    while ts_of(ch, lo) > t: lo = max(1, lo - int((th - t) / BT[ch]))
    while lo < hi:
        m = (lo + hi) // 2
        if ts_of(ch, m) < t: lo = m + 1
        else: hi = m
    return lo
