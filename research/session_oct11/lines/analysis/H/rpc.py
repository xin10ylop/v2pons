"""Polite read-only JSON-RPC to the public node: one POST at a time, >= 0.5 s apart, back-off on 429. Only the read methods below."""
import json, time, os, ssl, urllib.request
RPC = "https://rpc.mainnet.chain.robinhood.com"
ALLOWED = {"eth_call", "eth_getLogs", "eth_getTransactionByHash", "eth_getCode", "eth_getBlockByNumber", "eth_blockNumber", "eth_getStorageAt"}
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt") if os.path.exists("/root/.ccr/ca-bundle.crt") else None
_last = [0.0]; STATS = {"posts": 0, "items": 0, "r429": 0}
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rpc_log.jsonl")


def _post(body):
    for i in range(8):
        dt = time.time() - _last[0]
        if dt < 0.5: time.sleep(0.5 - dt)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(RPC, json.dumps(body).encode(), H)
            d = json.load(urllib.request.urlopen(req, timeout=60, context=CTX))
            STATS["posts"] += 1
            return d
        except urllib.error.HTTPError as e:
            if e.code == 429: STATS["r429"] += 1; time.sleep(2 * (i + 1)); continue
            raise
        except Exception as e:
            time.sleep(2 * (i + 1)); last = e
    raise RuntimeError("rpc failed")


def call(method, params):
    assert method in ALLOWED, method
    d = _post({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}); STATS["items"] += 1
    with open(LOG, "a") as f: f.write(json.dumps({"t": time.time(), "m": method, "n": 1}) + "\n")
    if "error" in d: raise RuntimeError(json.dumps(d["error"]))
    return d["result"]


def batch(method, plist):
    assert method in ALLOWED, method
    out = []
    for i in range(0, len(plist), 20):
        chunk = plist[i:i + 20]
        d = _post([{"jsonrpc": "2.0", "id": j, "method": method, "params": p} for j, p in enumerate(chunk)]); STATS["items"] += len(chunk)
        with open(LOG, "a") as f: f.write(json.dumps({"t": time.time(), "m": method, "n": len(chunk)}) + "\n")
        d = sorted(d, key=lambda x: x["id"])
        out += [x.get("result") for x in d]
    return out
