"""Read-only JSON-RPC helper for the flap v7 exit test (chain 56). Keyless public endpoints only; read methods only.
Never sends a transaction: the allow-list below has no send method."""
import json, time, urllib.request, threading
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
# head-state calls: the owner's listed endpoints. History (getLogs older than ~10k blocks, archive state) is refused by those
# (publicnode 403 beyond ~10k blocks, dataseeds "limit exceeded" on any getLogs, no archive), so history goes to the keyless
# public endpoints the bnbfreeze study used (sentio, blockmachine). No key anywhere.
URLS = ["https://bsc-rpc.publicnode.com", "https://bsc-dataseed.bnbchain.org", "https://bsc-dataseed1.defibit.io"]
HIST = ["https://bsc.rpc.sentio.xyz", "https://rpc-bsc.blockmachine.io"]
ALLOWED = {"eth_blockNumber", "eth_chainId", "eth_getLogs", "eth_getTransactionByHash", "eth_getBlockByNumber", "eth_getCode",
           "eth_call", "eth_getTransactionReceipt", "eth_getBalance", "eth_getStorageAt", "eth_getTransactionCount",
           "eth_getBlockReceipts"}
STATS = {}
_lk = threading.Lock()


class RPCError(Exception):
    pass


def _one(U, body, t=60):
    req = urllib.request.Request(U, json.dumps(body).encode(), H)
    return json.load(urllib.request.urlopen(req, timeout=t))


def call(m, p, urls=None, tries=3, t=60):
    assert m in ALLOWED, m
    last = None
    for attempt in range(tries):
        for U in (urls or URLS):
            try:
                r = _one(U, {"jsonrpc": "2.0", "id": 1, "method": m, "params": p}, t)
                if "result" in r:
                    with _lk: STATS[U] = STATS.get(U, 0) + 1
                    return r["result"]
                last = {"err": r.get("error"), "url": U}
                e = json.dumps(r.get("error")).lower()
                # execution reverted is a real answer for eth_call: return it
                if m == "eth_call" and ("revert" in e or "execution" in e):
                    return {"__revert__": r.get("error")}
            except Exception as ex:
                last = {"err": str(ex)[:200], "url": U}
        time.sleep(1 + attempt)
    raise RPCError(json.dumps(last)[:400])


def batch(calls, urls=None, t=90, tries=3):
    for m, _ in calls: assert m in ALLOWED, m
    body = [{"jsonrpc": "2.0", "id": i, "method": m, "params": p} for i, (m, p) in enumerate(calls)]
    last = None
    for attempt in range(tries):
        for U in (urls or URLS):
            try:
                r = _one(U, body, t)
                if isinstance(r, list):
                    out = {x["id"]: x for x in r}
                    if all(i in out and "result" in out[i] for i in range(len(calls))):
                        return [out[i]["result"] for i in range(len(calls))]
                    last = [out.get(i, {}).get("error") for i in range(len(calls)) if "result" not in out.get(i, {})][:2]
            except Exception as ex:
                last = str(ex)[:200]
        time.sleep(1 + attempt)
    # fall back to single calls
    return [call(m, p, urls) for m, p in calls]


def bn():
    return int(call("eth_blockNumber", []), 16)


def logs(address, topics, frm, to, urls=None):
    f = {"fromBlock": hex(frm), "toBlock": hex(to), "topics": topics}
    if address is not None: f["address"] = address
    return call("eth_getLogs", [f], urls=urls or HIST)


def logs_range(address, topics, frm, to, chunk=2000, urls=None, verbose=False):
    out = []; cur = frm; ch = chunk
    while cur <= to:
        end = min(to, cur + ch - 1)
        try:
            res = logs(address, topics, cur, end, urls)
        except RPCError as e:
            if ch <= 1: raise
            ch = max(1, ch // 2)
            if verbose: print("split", cur, end, str(e)[:100], "->", ch, flush=True)
            continue
        out.extend(res or []); cur = end + 1
        if len(res or []) < 2000 and ch < chunk: ch = min(chunk, ch * 2)
    return out


def ethcall(to, data, blk="latest", frm=None, urls=None):
    o = {"to": to, "data": data}
    if frm: o["from"] = frm
    return call("eth_call", [o, blk if isinstance(blk, str) else hex(blk)], urls=urls)
