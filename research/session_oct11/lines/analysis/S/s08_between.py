"""S08: what the launch wallet sends between its mint (nonce n+1) and its own first buy (nonce n+3): every tx of the launch wallet in the
blocks from the launch to the own buy, for the line's launches of the last 30 h (public RPC, read-only: full blocks) -> s08_between.out"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpc
from scommon import *
from s04_shapes import line_shape
D, R = load(); S1 = json.load(open(os.path.join(OUT, "s01_launches.json"))); TH = S1["t_head"]
out = []
for r in R:
    if not line_shape(r) or TH - r["ts"] > 30 * 3600 or not r["own1"]: continue
    bl = rpc.batch("eth_getBlockByNumber", [[hex(b), True] for b in range(r["lb"], r["lb"] + r["own1"]["off"] + 1)])
    mine = []; others = []
    for b in bl:
        for t in b["transactions"]:
            if t["from"].lower() == r["lw"]:
                mine.append((int(b["number"], 16) - r["lb"], int(t["nonce"], 16), (t.get("to") or "")[:12], t["input"][:10], (len(t["input"]) - 2) // 2, int(t["value"], 16) / 1e18))
            elif r["token"][2:] in t["input"].lower() or (t.get("to") or "").lower() == r["token"]:
                others.append((int(b["number"], 16) - r["lb"], t["from"][:10], (t.get("to") or "")[:12], t["input"][:10]))
    out.append(f"{r['lb']} {time.strftime('%m-%d %H:%M', time.gmtime(r['ts']))} {r['lw'][:10]} token {r['token']}: launch-wallet txs (off, nonce, to, sel, len, value) {mine}")
    out.append(f"    other txs touching the token before the own buy: {others}")
    print(out[-2]); print(out[-1])
open(os.path.join(OUT, "s08_between.out"), "w").write("\n".join(out) + "\n"); print(rpc.STATS)
