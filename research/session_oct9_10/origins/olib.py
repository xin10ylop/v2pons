"""block cache + scanning for the origins work. Chunks of 500 blocks stored gzip-json in origins/blk/<start>.json.gz
tx tuple: [bn, ts, hash, from, to, value_wei(str), nonce, type, sel, input_if_value>0_and_short]"""
import sys, os, json, gzip, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import post, rpc, batch, logs
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins/"
CH = 500
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
        time.sleep(0.05)
    return out
def _row(t, blk):
    v = int(t["value"], 16); inp = t["input"]
    return [int(blk["number"], 16), int(blk["timestamp"], 16), t["hash"], t["from"].lower(), (t.get("to") or "").lower(), str(v),
            int(t["nonce"], 16), t.get("type", "0x0"), inp[:10], inp if (v > 0 and len(inp) <= 6000) else (inp[:6000] if len(inp) > 10 and False else "")]
def chunk(c):
    p = D + "blk/%d.json.gz" % c
    if os.path.exists(p):
        try: return json.load(gzip.open(p, "rt"))
        except Exception: pass
    blks = _fetch(c, c + CH)
    rows = [_row(t, b) for b in blks for t in b["transactions"]]
    tsmap = {int(b["number"], 16): int(b["timestamp"], 16) for b in blks}
    data = {"rows": rows, "ts": tsmap}
    json.dump(data, gzip.open(p + ".tmp", "wt")); os.replace(p + ".tmp", p)
    return json.loads(json.dumps(data))
def rows(a, b):
    """all txs in blocks [a, b]"""
    out = []
    for c in range((a // CH) * CH, b + 1, CH):
        for r in chunk(c)["rows"]:
            if a <= r[0] <= b: out.append(r)
    return out
def utc(ts): return time.strftime("%m-%d %H:%M:%S", time.gmtime(ts))
_TS = {}
def bts(bn):
    if bn not in _TS: _TS[bn] = int(rpc("eth_getBlockByNumber", [hex(bn), False])["timestamp"], 16)
    return _TS[bn]
def touching(addrs, a, b, inp=True):
    s = {x.lower() for x in addrs}; out = []
    for r in rows(a, b):
        if r[3] in s or r[4] in s or (inp and r[9] and any(x[2:] in r[9] for x in s)): out.append(r)
    return out
def fmt(r, tag=None):
    return f"{r[0]} {utc(r[1])} {r[3]} -> {r[4]} {int(r[5])/1e18:.6f} n{r[6]} t{r[7]} {r[8]} {r[2][:14]}"
def nonce_now(w): return int(rpc("eth_getTransactionCount", [w, "latest"]), 16)
def bal_now(w): return int(rpc("eth_getBalance", [w, "latest"]), 16) / 1e18
