"""Read-only JSON-RPC to the public Robinhood Chain node: one request at a time, backoff on 429, a request log, a tx/block cache."""
import json, time, os, urllib.request, urllib.error
RPC = "https://rpc.mainnet.chain.robinhood.com"; H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = open(os.path.join(HERE, "rpc_log.jsonl"), "a")
ALLOWED = {"eth_getLogs", "eth_getTransactionByHash", "eth_getBlockByNumber", "eth_blockNumber"}


def post(body, what):
    for i in range(12):
        t = time.time()
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(body).encode(), H), timeout=90))
            LOG.write(json.dumps({"t": round(t, 2), "what": what, "ok": 1, "dt": round(time.time() - t, 2)}) + "\n"); LOG.flush()
            return r
        except urllib.error.HTTPError as e:
            LOG.write(json.dumps({"t": round(t, 2), "what": what, "http": e.code}) + "\n"); LOG.flush()
            ra = e.headers.get("Retry-After") if e.headers else None
            time.sleep(float(ra) if ra and ra.replace(".", "").isdigit() else (5 * (i + 1) if e.code == 429 else 3))
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
        ch = calls[i:i + size]
        for k in range(6):
            r = post([{"jsonrpc": "2.0", "id": j, "method": m, "params": p} for j, (m, p) in enumerate(ch)], f"batch{len(ch)}:{ch[0][0]}")
            if isinstance(r, list) and len(r) == len(ch) and all("result" in x for x in r): break
            time.sleep(4 * (k + 1))
        r = sorted(r, key=lambda x: x["id"]) if isinstance(r, list) else []
        out += [x.get("result") for x in r] if len(r) == len(ch) else [None] * len(ch)
    return out


def logs(flt, a, b):
    try: return rpc("eth_getLogs", [dict(flt, fromBlock=hex(a), toBlock=hex(b))])
    except RuntimeError as e:
        if b <= a: raise
        m = (a + b) // 2; return logs(flt, a, m) + logs(flt, m + 1, b)


class TxCache:
    def __init__(self, path):
        self.path = path; self.d = {}
        if os.path.exists(path):
            for l in open(path):
                try: x = json.loads(l); self.d[x["hash"]] = x
                except Exception: pass
        self.f = open(path, "a")

    def get(self, hashes):
        need = [h for h in dict.fromkeys(hashes) if h not in self.d]
        if need:
            res = batch([("eth_getTransactionByHash", [h]) for h in need])
            for h, t in zip(need, res):
                if t:
                    x = {k: t.get(k) for k in ("hash", "from", "to", "nonce", "value", "input", "blockNumber", "transactionIndex", "gasPrice", "maxPriorityFeePerGas")}
                    self.d[h] = x; self.f.write(json.dumps(x) + "\n")
            self.f.flush()
        return {h: self.d.get(h) for h in hashes}
