"""Where the 2.433 hub's money went: its two deposits (Oct 12 13:08:45 and 13:09:46 UTC) went to a Relay-style depository 0x794dbdbd
(selector 1e04ce08, a request id in the calldata); the Across deposit to chain 1 that followed was the solver's own rebalancing (sent by
the relayer 0x07ae8551 through 0x998d7c17 to a shared receiver), not the user's fill. A Relay-style solver fills the user on the destination
chain with a transaction that carries the request id in its calldata. This scans every block of each candidate chain from T-5 s to
T+240 s for a transaction whose input contains either request id. Public publicnode RPCs, read-only, paced."""
import json, sys, time, ssl, urllib.request, os
CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt")
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
IDS = {"f54cb4eb754dac0d266553696dbe4590e2e31f848d2b11733fa70c7771785871": ("test 0.1 ETH", 1791810525),
       "4d2bfc578db8b2a1c52ab51657f3c54fcab5743b7b97967ee0cb24760c4e770b": ("main 9.199 ETH", 1791810586)}
CH = {"ethereum": "https://ethereum-rpc.publicnode.com", "base": "https://base-rpc.publicnode.com", "arbitrum": "https://arbitrum-one-rpc.publicnode.com",
      "unichain": "https://unichain-rpc.publicnode.com", "bsc": "https://bsc-rpc.publicnode.com", "optimism": "https://optimism-rpc.publicnode.com"}
last = [0.0]
def post(url, body):
    for i in range(12):
        dt = time.time() - last[0]
        if dt < 0.5: time.sleep(0.5 - dt)
        last[0] = time.time()
        try: return json.load(urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(), H), timeout=60, context=CTX))
        except Exception as e:
            err = e; time.sleep(min(20, 2 * (i + 1)))
    raise RuntimeError("rpc failed %s %s" % (url, err))
def call(url, m, p):
    d = post(url, {"jsonrpc": "2.0", "id": 1, "method": m, "params": p})
    if "error" in d: raise RuntimeError(str(d["error"])[:200])
    return d["result"]
def ts(url, n): return int(call(url, "eth_getBlockByNumber", [hex(n), False])["timestamp"], 16)
def block_at(url, t):
    hi = int(call(url, "eth_blockNumber", []), 16); th = ts(url, hi)
    lo = max(1, hi - 1); step = 1
    while ts(url, lo) > t:                      # gallop back
        step *= 2; lo = max(1, hi - step)
    while lo < hi:
        m = (lo + hi) // 2
        if ts(url, m) < t: lo = m + 1
        else: hi = m
    return lo
chains = sys.argv[1].split(",") if len(sys.argv) > 1 else list(CH)
t0, t1 = 1791810525 - 5, 1791810586 + 240
for c in chains:
    url = CH[c]
    try:
        a = block_at(url, t0); b = block_at(url, t1)
    except Exception as e:
        print(c, "refused/failed:", str(e)[:200], flush=True); continue
    print(c, "blocks", a, "..", b, flush=True)
    found = 0
    for k in range(a, b + 1, 5):
        body = [{"jsonrpc": "2.0", "id": j, "method": "eth_getBlockByNumber", "params": [hex(n), True]} for j, n in enumerate(range(k, min(b, k + 4) + 1))]
        try: res = post(url, body)
        except Exception as e: print("  fail", k, str(e)[:100]); continue
        if isinstance(res, dict): res = [res]
        for r in res:
            blk = r.get("result")
            if not blk: continue
            for t in blk["transactions"]:
                inp = t.get("input", "")
                for rid, (nm, tt) in IDS.items():
                    if rid in inp:
                        found += 1
                        print("  FOUND", nm, c, "block", int(blk["number"], 16), "ts", int(blk["timestamp"], 16), "(+%ds)" % (int(blk["timestamp"], 16) - tt),
                              "tx", t["hash"], "from", t["from"], "to", t.get("to"), "value", int(t["value"], 16) / 1e18, "input len", (len(inp) - 2) // 2, flush=True)
    print(c, "done, matches", found, flush=True)
