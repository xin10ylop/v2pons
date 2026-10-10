"""cached full-block fetch (chunks of 200 blocks, gzip json in origins/eras/blk). row: [bn, ts, hash, from, to, value_wei_str, nonce, type, sel]"""
import gzip
from L import *
CH = 200
def _fetch(lo, hi, bs=50):
    out = []
    for s in range(lo, hi, bs):
        e = min(hi, s + bs)
        for k in range(15):
            try: r = post([{"jsonrpc": "2.0", "id": j, "method": "eth_getBlockByNumber", "params": [hex(b), True]} for j, b in enumerate(range(s, e))])
            except RuntimeError: r = None
            if isinstance(r, list) and len(r) == e - s and all(x.get("result") for x in r): break
            if isinstance(r, list) and any("too large" in str(x.get("error")) for x in r):
                if e - s == 1: raise RuntimeError("single block too large %d" % s)
                r = "split"; break
            time.sleep(2 + 2 * k)
        else: raise RuntimeError("blocks %d" % s)
        if r == "split": out += _fetch(s, e, max(1, (e - s) // 5)); continue
        out += [x["result"] for x in sorted(r, key=lambda x: x["id"])]
        time.sleep(0.1)
    return out
def chunk(c):
    p = D + "blk/%d.json.gz" % c
    if os.path.exists(p):
        try: return json.load(gzip.open(p, "rt"))
        except Exception: pass
    blks = _fetch(c, c + CH)
    rows = [[int(b["number"], 16), int(b["timestamp"], 16), t["hash"], t["from"].lower(), (t.get("to") or "").lower(), str(int(t["value"], 16)),
             int(t["nonce"], 16), t.get("type", "0x0"), t["input"][:10]] for b in blks for t in b["transactions"]]
    json.dump(rows, gzip.open(p + ".tmp", "wt")); os.replace(p + ".tmp", p)
    return rows
def rows(a, b):
    out = []
    for c in range((a // CH) * CH, b + 1, CH):
        out += [r for r in chunk(c) if a <= r[0] <= b]
    return out
def touching(addrs, a, b):
    s = {x.lower() for x in addrs}
    return [r for r in rows(a, b) if r[3] in s or r[4] in s]
def utc(ts): return time.strftime("%m-%d %H:%M:%S", time.gmtime(ts))
def fmt(r, ref=None):
    return f"{r[0]}{'' if ref is None else ' (%+d)' % (r[0] - ref)} {utc(r[1])} {r[3]} -> {r[4]} {int(r[5])/1e18:.5f} n{r[6]} {r[8]}"
