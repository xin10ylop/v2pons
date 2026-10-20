import sys, json, time, os, gzip
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import post, rpc, batch, logs, PM, T_SWAP, T_ML, W, sgn, keccak
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/"
T_TR = "0x" + keccak(text="Transfer(address,address,uint256)").hex(); T_AP = "0x" + keccak(text="Approval(address,address,uint256)").hex()
def utc(ts): return time.strftime("%m-%d %H:%M:%S", time.gmtime(ts))
def getblocks(lo, hi, bs=50):
    """full blocks lo..hi-1 (splits a batch whose response is too large)"""
    out = []
    for s in range(lo, hi, bs):
        e = min(hi, s + bs)
        for k in range(12):
            try: r = post([{"jsonrpc": "2.0", "id": j, "method": "eth_getBlockByNumber", "params": [hex(b), True]} for j, b in enumerate(range(s, e))])
            except RuntimeError: r = None
            if isinstance(r, list) and len(r) == e - s and all(x.get("result") for x in r): break
            if isinstance(r, list) and any("too large" in str(x.get("error")) for x in r):
                if e - s == 1: raise RuntimeError("single block too large %d" % s)
                r = None; break
            time.sleep(1.5 + 1.5 * k)
        else: raise RuntimeError("blocks %d" % s)
        if r is None: out += getblocks(s, e, max(1, (e - s) // 5)); continue
        out += [x["result"] for x in sorted(r, key=lambda x: x["id"])]
    return out
def T(t, blk):
    return {"bn": int(blk["number"], 16), "ts": int(blk["timestamp"], 16), "hash": t["hash"], "from": t["from"].lower(), "to": (t.get("to") or "").lower(),
            "value": int(t["value"], 16) / 1e18, "sel": t["input"][:10], "nonce": int(t["nonce"], 16), "ilen": len(t["input"])}
def scan(a, b, pred, backwards=False, stop=None, step=500):
    """scan blocks [a, b] for txs with pred(T) true; stop(hits) -> True ends early"""
    hits = []
    rng = range(b, a - 1, -step) if backwards else range(a, b + 1, step)
    for s in rng:
        lo, hi = (max(a, s - step + 1), s + 1) if backwards else (s, min(b + 1, s + step))
        blks = getblocks(lo, hi)
        if backwards: blks = blks[::-1]
        for blk in blks:
            for t in (blk["transactions"][::-1] if backwards else blk["transactions"]):
                x = T(t, blk)
                if pred(x, t): hits.append(x)
        if stop and stop(hits): break
    return hits
def nonce_now(w): return int(rpc("eth_getTransactionCount", [w, "latest"]), 16)
