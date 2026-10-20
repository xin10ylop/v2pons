"""Minimal read-only JSON-RPC client. One request in flight; backs off on 429.
Only eth_blockNumber, eth_getLogs, eth_getTransactionByHash, eth_getBlockByNumber are allowed."""
import json, time, requests, sys
ALLOWED = {"eth_blockNumber", "eth_getLogs", "eth_getTransactionByHash", "eth_getBlockByNumber"}
S = requests.Session()
STATS = {}

class RPCError(Exception):
    pass

def call(url, method, params, timeout=30, max_retries=6):
    assert method in ALLOWED, method
    st = STATS.setdefault(url, {"ok": 0, "err": 0, "429": 0, "lat": 0.0, "errs": {}})
    delay = 1.0
    for attempt in range(max_retries):
        t0 = time.time()
        try:
            r = S.post(url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=timeout,
                       headers={"content-type": "application/json"})
        except requests.RequestException as e:
            st["err"] += 1; st["errs"][type(e).__name__] = st["errs"].get(type(e).__name__, 0) + 1
            time.sleep(delay); delay *= 2; continue
        st["lat"] += time.time() - t0
        if r.status_code == 429:
            st["429"] += 1; time.sleep(delay); delay *= 2; continue
        if r.status_code >= 500 or r.status_code in (403, 404, 405):
            st["err"] += 1; st["errs"][f"http{r.status_code}"] = st["errs"].get(f"http{r.status_code}", 0) + 1
            if r.status_code in (403, 404, 405):
                raise RPCError(f"http {r.status_code}: {r.text[:200]}")
            time.sleep(delay); delay *= 2; continue
        try:
            j = r.json()
        except Exception:
            st["err"] += 1; time.sleep(delay); delay *= 2; continue
        if "error" in j:
            msg = json.dumps(j["error"])[:300]
            low = msg.lower()
            if "rate" in low and "limit" in low or "too many requests" in low:
                st["429"] += 1; time.sleep(delay); delay *= 2; continue
            st["err"] += 1; k = msg[:80]; st["errs"][k] = st["errs"].get(k, 0) + 1
            raise RPCError(msg)
        st["ok"] += 1
        return j["result"]
    raise RPCError(f"retries exhausted for {method}")

def block_number(url):
    return int(call(url, "eth_blockNumber", []), 16)

def get_block(url, n, full=False):
    tag = n if isinstance(n, str) else hex(n)
    return call(url, "eth_getBlockByNumber", [tag, full])

def get_tx(url, h):
    return call(url, "eth_getTransactionByHash", [h])

def get_logs_range(url, address, topics, frm, to, chunk=10000, min_chunk=1, max_chunk=None, log=None):
    """Adaptive chunked eth_getLogs over [frm, to]. Halves chunk on error, grows on success."""
    out = []
    cur = frm
    max_chunk = max_chunk or chunk * 8
    while cur <= to:
        end = min(to, cur + chunk - 1)
        flt = {"fromBlock": hex(cur), "toBlock": hex(end), "topics": topics}
        if address is not None:
            flt["address"] = address
        try:
            res = call(url, "eth_getLogs", [flt])
        except RPCError as e:
            if chunk <= min_chunk:
                raise
            chunk = max(min_chunk, chunk // 2)
            if log is not None:
                log.append(f"getLogs err at {cur}-{end}: {str(e)[:120]} -> chunk {chunk}")
            continue
        out.extend(res)
        cur = end + 1
        if len(res) < 2000 and chunk < max_chunk:
            chunk = min(max_chunk, int(chunk * 1.5))
    return out, chunk
