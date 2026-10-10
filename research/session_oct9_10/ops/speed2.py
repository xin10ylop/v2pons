import sys, time, json, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import RPC, H
import urllib.error
def raw(body):
    t = time.time()
    try:
        r = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(body).encode(), H), timeout=90)); ok = isinstance(r, list) and all("result" in x for x in r)
        return ok, time.time() - t, None
    except urllib.error.HTTPError as e: return False, time.time() - t, e.code
def test(bs, th, n, base):
    t0 = time.time(); res = []
    def one(i):
        s = base + i * bs
        return raw([{"jsonrpc": "2.0", "id": j, "method": "eth_getBlockByNumber", "params": [hex(b), True]} for j, b in enumerate(range(s, s + bs))])
    with ThreadPoolExecutor(th) as ex: res = list(ex.map(one, range(n)))
    dt = time.time() - t0; ok = sum(1 for r in res if r[0])
    print(f"batch {bs} threads {th}: {n} reqs in {dt:.1f}s ok {ok} codes {[r[2] for r in res if not r[0]][:5]} blocks/s {ok*bs/dt:.0f} mean lat {sum(r[1] for r in res)/n:.2f}", flush=True)
test(50, 1, 10, 84000000)
test(100, 1, 10, 84010000)
test(50, 2, 20, 84020000)
test(50, 4, 20, 84030000)
test(25, 4, 40, 84040000)
