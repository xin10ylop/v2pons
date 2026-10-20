"""Minimal read-only JSON-RPC client: one request in flight, fixed polite gap, honest User-Agent, backs off on 429."""
import json, time, urllib.request, urllib.error, sys
UA = {"Content-Type": "application/json", "User-Agent": "arb-scout/0.1 (read-only research)"}
GAP = 0.5
_last = [0.0]
LOG = []
def post(url, body, tries=6):
    for i in range(tries):
        g = time.time() - _last[0]
        if g < GAP: time.sleep(GAP - g)
        _last[0] = time.time(); t0 = time.time()
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(), UA), timeout=60)
            out = json.loads(r.read()); LOG.append((url, "ok", round(time.time() - t0, 3))); return out
        except urllib.error.HTTPError as e:
            LOG.append((url, e.code, round(time.time() - t0, 3)))
            if e.code == 429: time.sleep(5 * (i + 1)); continue
            return {"http_error": e.code, "body": e.read()[:300].decode(errors="replace")}
        except Exception as e:
            LOG.append((url, "exc", str(e)[:80])); time.sleep(2 * (i + 1))
    return {"failed": True}
def rpc(url, m, p):
    return post(url, {"jsonrpc": "2.0", "id": 1, "method": m, "params": p})
