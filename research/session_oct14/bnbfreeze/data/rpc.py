"""read-only JSON-RPC helper for the bnbfreeze/data study: public keyless endpoints only, one request in flight, back-off on
429/limit, endpoint fallback, JSON-RPC batches. No key, no transaction: eth_getLogs, eth_getTransactionByHash, eth_getTransactionReceipt,
eth_getBlockByNumber, eth_getCode, eth_call only."""
import json, time, urllib.request
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (research; read-only)"}
URLS = {"se": "https://bsc.rpc.sentio.xyz", "bm": "https://rpc-bsc.blockmachine.io", "pk": "https://bsc.api.pocket.network",
        "48": "https://rpc-bsc.48.club", "pn": "https://bsc-rpc.publicnode.com", "ds": "https://bsc-dataseed.bnbchain.org",
        "df": "https://bsc-dataseed1.defibit.io"}
ARCHIVE = ("se", "bm", "pk")
STATS = {}
def _post(u, body, timeout=90):
    req = urllib.request.Request(u, json.dumps(body).encode(), H)
    return json.load(urllib.request.urlopen(req, timeout=timeout))
def call(method, params, order=ARCHIVE, retries=5, raw=False):
    last = None
    for k in order:
        d = 0.5
        for _ in range(retries):
            try:
                j = _post(URLS[k], {"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
                STATS[k] = STATS.get(k, 0) + 1
                if "error" in j:
                    s = str(j["error"]).lower(); last = (k, j["error"])
                    if any(x in s for x in ("limit", "rate", "too many", "busy", "timeout")): time.sleep(d); d *= 2; continue
                    if raw: return j
                    break
                return j if raw else j["result"]
            except Exception as e:
                last = (k, str(e)[:160]); time.sleep(d); d *= 2
    if raw: return {"error": str(last)}
    raise RuntimeError(f"{method} failed: {last}")
def batch(reqs, order=ARCHIVE, size=50, retries=4):
    """reqs: [(method, params)] -> list of raw responses (dict with result or error), in order"""
    out = [None] * len(reqs)
    for i in range(0, len(reqs), size):
        chunk = reqs[i:i + size]; body = [{"jsonrpc": "2.0", "id": j, "method": m, "params": p} for j, (m, p) in enumerate(chunk)]
        got = None
        for k in order:
            d = 0.5
            for _ in range(retries):
                try:
                    r = _post(URLS[k], body)
                    if isinstance(r, list) and len(r) == len(chunk) and not any("error" in x and any(s in str(x["error"]).lower() for s in ("limit", "rate", "too many")) for x in r):
                        got = {x["id"]: x for x in r}; break
                    time.sleep(d); d *= 2
                except Exception:
                    time.sleep(d); d *= 2
            if got: break
        if not got:   # fall back to single calls
            got = {j: call(m, p, order=order, raw=True) for j, (m, p) in enumerate(chunk)}
        for j in range(len(chunk)): out[i + j] = got[j]
    return out
def logs(flt, a, b, step=5000, order=ARCHIVE):
    """eth_getLogs over [a, b] in chunks; a chunk that errors is split"""
    res = []; x = a
    while x <= b:
        e = min(b, x + step - 1)
        try:
            r = call("eth_getLogs", [dict(flt, fromBlock=hex(x), toBlock=hex(e))], order=order)
        except RuntimeError as err:
            if step > 50: res += logs(flt, x, e, step=max(50, step // 4), order=order); x = e + 1; continue
            raise
        res += r; x = e + 1
    return res
