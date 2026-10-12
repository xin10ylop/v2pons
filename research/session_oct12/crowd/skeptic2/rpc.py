"""skeptic2: polite read-only JSON-RPC to the public Robinhood Chain node only. One POST at a time, >= 0.6 s apart, back-off on 429.
Read methods only; no keys, no transactions."""
import json, time, os, ssl, urllib.request, urllib.error
RPC = "https://rpc.mainnet.chain.robinhood.com"
ALLOWED = {"eth_getLogs", "eth_getTransactionByHash", "eth_getTransactionReceipt", "eth_getCode", "eth_getBlockByNumber", "eth_blockNumber",
           "eth_chainId", "eth_getBalance", "eth_getTransactionCount", "eth_call"}
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt") if os.path.exists("/root/.ccr/ca-bundle.crt") else None
_last = [0.0]; STATS = {"posts": 0, "items": 0, "r429": 0}
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rpc_log.jsonl")
def _post(body):
    err = None
    for i in range(10):
        dt = time.time() - _last[0]
        if dt < 0.6: time.sleep(0.6 - dt)
        _last[0] = time.time()
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(body).encode(), H), timeout=60, context=CTX))
            STATS["posts"] += 1; return d
        except urllib.error.HTTPError as e:
            err = e
            if e.code == 429: STATS["r429"] += 1; time.sleep(2 * (i + 1)); continue
            raise
        except Exception as e:
            err = e; time.sleep(2 * (i + 1))
    raise RuntimeError(f"rpc failed: {err}")
def _log(m, n):
    with open(LOG, "a") as f: f.write(json.dumps({"t": time.time(), "m": m, "n": n}) + "\n")
def call(method, params):
    assert method in ALLOWED, method
    d = _post({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}); STATS["items"] += 1; _log(method, 1)
    if "error" in d: raise RuntimeError(json.dumps(d["error"])[:300])
    return d["result"]
def batch(method, plist, n=20):
    assert method in ALLOWED, method
    out = []
    for i in range(0, len(plist), n):
        chunk = plist[i:i + n]
        for attempt in range(6):
            d = _post([{"jsonrpc": "2.0", "id": j, "method": method, "params": p} for j, p in enumerate(chunk)]); _log(method, len(chunk))
            if isinstance(d, list) and all("result" in x for x in d): break
            time.sleep(3 * (attempt + 1))
        else:
            raise RuntimeError("batch failed: " + json.dumps(d)[:300])
        STATS["items"] += len(chunk)
        d = sorted(d, key=lambda x: x["id"]); out += [x.get("result") for x in d]
    return out
def logs(flt, a, b):
    try: return call("eth_getLogs", [dict(flt, fromBlock=hex(a), toBlock=hex(b))])
    except RuntimeError:
        if b <= a: raise
        m = (a + b) // 2; return logs(flt, a, m) + logs(flt, m + 1, b)
