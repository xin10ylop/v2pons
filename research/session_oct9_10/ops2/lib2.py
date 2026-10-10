"""ops2 helpers: the shared bc block cache (ops/lch/bc) with a gentler RPC post (batches <= 50, long backoff on 429/errors)."""
import sys, os, json, time, random, urllib.request, urllib.error
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
import bc
from chain import RPC, H
O = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2/"
def gentle_post(body):
    for i in range(40):
        try:
            bc.STATS["req"] += 1
            r = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps(body).encode(), H), timeout=90))
            time.sleep(0.15)
            return r
        except urllib.error.HTTPError as e:
            bc.STATS["429"] += 1; time.sleep(min(30, 2 + 1.5 * i) + random.random())
        except Exception: time.sleep(min(30, 2 + i))
    raise RuntimeError("rpc")
bc.post = gentle_post
def have(c):
    return os.path.exists(bc.D + "%d.json" % (c * bc.CH // 1000)) or os.path.exists(bc.D + "q%d.json" % c)
def missing(lo, hi):
    return [c for c in range(lo // bc.CH, hi // bc.CH + 1) if not have(c)]
def R(bn, ts, t):
    return {"bn": bn, "utc": time.strftime("%m-%d %H:%M:%S", time.gmtime(ts)), "hash": t[0], "from": t[1], "to": t[2], "eth": int(t[3]) / 1e18,
            "nonce": t[4], "sel": t[5], "len": t[6]}
def touching(addrs, lo, hi, cached_only=False):
    A = {a.lower() for a in addrs}; out = []
    for c in range(lo // bc.CH, hi // bc.CH + 1):
        if cached_only and not have(c): continue
        d = bc.chunk(c)
        for bn in range(max(lo, c * bc.CH), min(hi, c * bc.CH + bc.CH - 1) + 1):
            if bn in d:
                ts, tl = d[bn]
                for t in tl:
                    if t[1] in A or t[2] in A: out.append(R(bn, ts, t))
    return out
def fmt(r, lab=None):
    lab = lab or {}
    return f'{r["bn"]} {r["utc"]} {r["from"]} {lab.get(r["from"], "")}-> {r["to"]} {lab.get(r["to"], "")} {r["eth"]:.6f} n{r["nonce"]} {r["sel"]} {r["hash"][:14]}'
