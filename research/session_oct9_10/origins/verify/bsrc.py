"""For Base senders into a collector: find the funding tx (binary search on historical balance, up to 300 blocks back),
then ask Relay API (v2 by fill hash) for origin chain + depositor. Input lines: '<block> <date> <time> <sender> -> <to> <eth> ...'"""
import sys, json, time, urllib.request
RPC = "https://mainnet.base.org"; H = {"Content-Type": "application/json", "User-Agent": "curl/8.5.0"}
def rpc(m, p):
    for i in range(8):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), H), timeout=60))
            if "error" in r: raise RuntimeError(str(r["error"])[:200])
            return r["result"]
        except Exception as e: err = e; time.sleep(1.5 * (i + 1))
    raise RuntimeError(str(err))
def relay(h):
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request("https://api.relay.link/requests/v2?hash=" + h, headers={"User-Agent": "curl/8.5.0"}), timeout=30))
        out = []
        for x in d.get("requests", []):
            ins = [(t.get("chainId"), t.get("hash"), (t.get("data") or {}).get("from")) for t in x["data"].get("inTxs", [])]
            out.append({"id": x["id"][:18], "user": x.get("user"), "recipient": x.get("recipient"), "in": ins, "depositor": (x.get("depositAddress") or {}).get("depositor")})
        return out
    except Exception as e: return str(e)[:100]
for line in open(sys.argv[1]):
    p = line.split()
    if len(p) < 7 or p[4] != "->" or p[3] == p[5]: continue
    s, fb = p[3].lower(), int(p[0])
    if s.startswith("0x487cab40"): continue
    bal = lambda b: int(rpc("eth_getBalance", [s, hex(b)]), 16)
    lo, hi = fb - 300, fb
    if bal(lo) > 0: print(s, "funded before", lo); continue
    while lo < hi:
        m = (lo + hi) // 2
        if bal(m) > 0: hi = m
        else: lo = m + 1
    blk = rpc("eth_getBlockByNumber", [hex(lo), True]); found = False
    for t in blk["transactions"]:
        if (t.get("to") or "").lower() == s:
            found = True
            rl = relay(t["hash"]); time.sleep(2.5)
            print(json.dumps({"sender": s, "fwd_block": fb, "fwd_eth": float(p[6]), "fund_block": lo, "funder": t["from"], "funder_nonce": int(t["nonce"], 16), "fund_eth": int(t["value"], 16) / 1e18, "fund_input": t["input"][:74], "fund_hash": t["hash"], "relay": rl}), flush=True)
    if not found: print(json.dumps({"sender": s, "fund_block": lo, "funder": "internal (no direct tx)"}), flush=True)
    time.sleep(0.5)
