"""Scan full Robinhood blocks [a,b] and print txs whose from or to is in the watch set (or all value txs with --all).
usage: scan.py a b addr1,addr2,... [--all]"""
import sys, json, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import batch
a, b = int(sys.argv[1]), int(sys.argv[2]); watch = set(x.lower() for x in sys.argv[3].split(",") if x)
allv = "--all" in sys.argv
for s in range(a, b + 1, 25):
    bl = batch([("eth_getBlockByNumber", [hex(n), True]) for n in range(s, min(b, s + 24) + 1)])
    for blk in bl:
        if not blk: continue
        n = int(blk["number"], 16); ts = time.strftime("%m-%d %H:%M:%S", time.gmtime(int(blk["timestamp"], 16)))
        for t in blk["transactions"]:
            f = t["from"].lower(); to = (t.get("to") or "").lower(); v = int(t["value"], 16) / 1e18
            if (f in watch or to in watch) or (allv and v > 0):
                print(n, ts, f, "->", to, round(v, 6), "n", int(t["nonce"], 16), t["type"], t["input"][:10], t["hash"][:14], flush=True)
    time.sleep(0.3)
