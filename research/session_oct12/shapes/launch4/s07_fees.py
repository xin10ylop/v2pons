"""The hooks' take, from receipts: an S2 launcher sell, the S2 runner's first outside buy, and an S1 buy and sell (0xafa54e69). Prints each
receipt's Transfer and Swap logs, so the WETH/USDG actually paid or received can be compared with the Swap event's amounts (s07_fees.out)."""
from common import *
import rpc
D = json.load(open(J("s06_pools.json"))); P = {p["pid"]: p for p in D["pools"]}
pick = []
s2 = [p for p in D["pools"] if p["shape"] == "S2"]
ls = next(w for w in s2[0]["sw"] if not w["inlaunch"] and w["from"] == s2[0]["launcher"]); pick.append(("S2 launcher sell", s2[0], ls))
run = next(p for p in s2 if p["pid"].startswith("0xc1ffeb85")); pick.append(("S2 runner first outside buy", run, next(w for w in run["sw"] if not w["inlaunch"])))
pick.append(("S2 runner first outside sell", run, next(w for w in run["sw"] if not w["inlaunch"] and not w["buy"])))
s1 = next(p for p in D["pools"] if p["shape"] == "S1" and p["pid"].startswith("0x25a7019f"))
for w in s1["sw"][:2]: pick.append(("S1 " + ("buy" if w["buy"] else "sell"), s1, w))
for name, p, w in pick:
    rc = rpc.call("eth_getTransactionReceipt", [w["tx"]])
    print(f"== {name}: pool {p['pid'][:10]} quote {p['qname']} off {w['off']} from {w['from']} swap-event quote {w['q']} coin {w['c']} buy {w['buy']} swfee {w['swfee']}")
    for l in rc["logs"]:
        t0 = l["topics"][0] if l["topics"] else ""
        if t0 == T_TRANSFER and len(l["topics"]) == 3:
            print(f"    Transfer {l['address'][:10]} {l['topics'][1][-40:][:10]} -> {l['topics'][2][-40:][:10]} {int(l['data'], 16)}")
        elif t0 == T_SWAP:
            print(f"    Swap pool {l['topics'][1][:10]} a0 {sgn(W(l['data'], 0))} a1 {sgn(W(l['data'], 1))} fee {W(l['data'], 5)}")
        else:
            print(f"    log {l['address'][:10]} {t0[:10]} data {len(l['data']) // 2 - 1} B")
print(rpc.STATS)
