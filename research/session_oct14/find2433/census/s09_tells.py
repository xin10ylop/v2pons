"""Step 9: launches after the last 2.433 launch (block 86310320) carrying any 2.433 tell, across every shape:
value within 10% of 2.4333285 ETH (or exactly 2.4333285 anywhere in the tx value), the 2.433 sqrtPriceX96 (exact or within 3%), fee 5000/ts 100,
gas limit exactly 15,000,000, a token ending in 777 (code size/hash checked in s09b), the bot router as tx target or as launcher-funded router.
Prints s09_tells.out and writes s09_tells.json."""
import collections
from common import *
rows = launches()
STOP = 86310320
after = [r for r in rows if r["b"] > STOP]
print("launches after the stop (block > %d): %d (v4 %d, v3 %d)" % (STOP, len(after), sum(r["ven"] == "v4" for r in after), sum(r["ven"] == "v3" for r in after)))
out = {}
def show(name, xs):
    print("\n== %s: %d" % (name, len(xs)))
    c = collections.Counter((r["fam"] or r["key"]) for r in xs)
    for k, v in c.most_common(12): print("  %4d %s" % (v, k))
    out[name] = [dict(b=r["b"], t=hm(r["t"]), pid=r["pid"], frm=r["frm"], to=r["to"], v=r["v"], fee=r["fee"], ts=r["ts"], tok=r["tok"], fam=r["fam"] or r["key"], gas=r["gas"]) for r in xs][:200]
show("value exactly 2.4333285 ETH", [r for r in after if int(r["v"]) == V2433])
show("value 2.19-2.68 ETH (10%)", [r for r in after if 0.9 * V2433 <= int(r["v"]) <= 1.1 * V2433])
show("sqrtP exactly 2.433", [r for r in after if r["sqrtp"] and int(r["sqrtp"]) == SQRTP_2433])
show("sqrtP within 3% of 2.433 (ETH as currency0)", [r for r in after if r["sqrtp"] and r["c0"] == E and abs(int(r["sqrtp"]) / SQRTP_2433 - 1) <= 0.03])
show("fee 5000 / ts 100", [r for r in after if r["fee"] == 5000 and r["ts"] == 100])
show("fee 2500 / ts 50", [r for r in after if r["fee"] == 2500 and r["ts"] == 50])
show("gas limit exactly 15,000,000", [r for r in after if r["gas"] == 15_000_000])
show("gas limit exactly 15,000,000, not VB 3.0/5.0", [r for r in after if r["gas"] == 15_000_000 and r["fam"] not in ("VB 3.0", "VB 5.0")])
show("token ending 777, not VB 3.0/5.0", [r for r in after if r["tok"].endswith("777") and r["fam"] not in ("VB 3.0", "VB 5.0")])
show("tx sent to the bot router 0x1cbaf24d", [r for r in after if r["to"] == BOT])
show("launch sender nonce exactly 11 (2.433 launch nonce), POSM ETH, not VB 3.0/5.0", [r for r in after if r["n"] == 11 and r["to"] == POSM and r["q"] == "ETH" and r["fam"] not in ("VB 3.0", "VB 5.0")])
show("POSM 1444 B ETH value >= 1 ETH, not VB 3.0/5.0", [r for r in after if r["to"] == POSM and r["clen"] == 1444 and r["q"] == "ETH" and int(r["v"]) >= 10**18 and r["fam"] not in ("VB 3.0", "VB 5.0")])
jdump(out, "s09_tells.json")
