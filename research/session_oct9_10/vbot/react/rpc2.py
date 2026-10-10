"""patient JSON-RPC (the public endpoint is shared with sibling jobs and rate limits): retries up to ~15 min, batches <= 50"""
import json, time, urllib.request, urllib.error, sys
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import RPC, H
def post(body):
    for i in range(60):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(body).encode(), H), timeout=90))
        except urllib.error.HTTPError as e: time.sleep(min(30, 3 * (i + 1)))
        except Exception: time.sleep(min(30, 2 + i))
    raise RuntimeError("rpc")
def rpc(m, p):
    r = post({"jsonrpc": "2.0", "id": 1, "method": m, "params": p})
    if "error" in r: raise RuntimeError(str(r["error"])[:200])
    return r["result"]
def batch(calls, n=50):
    out = []
    for i in range(0, len(calls), n):
        ch = calls[i:i + n]
        r = post([{"jsonrpc": "2.0", "id": j, "method": m, "params": p} for j, (m, p) in enumerate(ch)])
        d = {x["id"]: x.get("result") for x in r}; out += [d.get(j) for j in range(len(ch))]
    return out
