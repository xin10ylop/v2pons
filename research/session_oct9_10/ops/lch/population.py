"""Every launch ever made through launcher 0x3194e326 (7,485 Launched events, block 19.37M = 2026-07-25 -> now): who sent them, nonce,
recipient, metadata host, value, fee, gas fingerprint, by week."""
import json, collections, sys, time
sys.path.insert(0, ".")
from decode import dec
T = json.load(open("../launcher_txs.json")); L = json.load(open("../launcher_logs.json"))
lg = {x["transactionHash"]: x for x in L}
rows = []
for h, t in T.items():
    d = dec(t["input"]); x = lg[h]
    rows.append(dict(h=h, bn=t["bn"], frm=t["from"], nonce=t["nonce"], eth=t["value"] / 1e18, sel=t["input"][:10], len=len(t["input"]) // 2 - 1,
                     host=d.get("s3", "?").split("/metadata/")[0] if "s3" in d else "ERR", pref=(d.get("s3", "").split("/metadata/")[-1].split("_")[1] if "_auto_" in d.get("s3", "") else "plain"),
                     recip_is_sender=(d.get("recipient", "").lower() == t["from"]), topic1=("0x" + x["topics"][1][-40:]), fee=d.get("fee"), ts=d.get("tickSpacing"),
                     tl=d.get("tickLower"), tu=d.get("tickUpper"), supply=d.get("u84"), type=t["type"], tip=int(t["tip"], 16) if t.get("tip") else None, gas=t["gas"],
                     createdOn=None))
rows.sort(key=lambda r: r["bn"])
json.dump(rows, open("population.json", "w"))
C = collections.Counter
print("launches", len(rows), "distinct senders", len(set(r["frm"] for r in rows)))
print("sender nonce at launch:", C(min(r["nonce"], 5) if r["nonce"] < 5 else ">=5" for r in rows))
print("selector:", C(r["sel"] for r in rows), "calldata len:", C(r["len"] for r in rows).most_common(5))
print("metadata host:", C(r["host"] for r in rows))
print("metadata file prefix (launch_auto_ vs launch_):", C(r["pref"] for r in rows))
print("recipient == sender:", C(r["recip_is_sender"] for r in rows), " event topic1 == sender:", C(r["topic1"] == r["frm"] for r in rows))
print("tick range:", C((r["tl"], r["tu"], r["ts"]) for r in rows).most_common(5))
print("supply:", C(r["supply"] for r in rows).most_common(5))
print("tx type / tip:", C((r["type"], r["tip"]) for r in rows).most_common(8))
print("gas limit:", C(r["gas"] for r in rows).most_common(8))
ms = C(r["frm"] for r in rows); multi = [(a, n) for a, n in ms.items() if n > 1]
print("senders with >1 launch:", len(multi), sorted(multi, key=lambda x: -x[1])[:10])
# by block bucket ~ week (0.1s blocks -> 6.048M blocks/week roughly; use real timestamps of a few blocks instead)
