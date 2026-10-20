"""Oct 9 B launches 09:24 (0x758c3c5f) and 10:48 (0x2a928e99): deployer funding back 3 hops; deployer's txs after the pull, and the next hop."""
import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops")
from bcx import *
from sets import Bsys, Asys, B, A
lab = {w: "B" for w in B}; lab.update({w: "A" for w in A})
L = json.load(open(D + "b_launches.json"))
res = {}
for pid in [k for k in L if k[:10] in ("0x758c3c5f", "0x2a928e99")]:
    p = L[pid]; dep = p["deployer"]; b0 = p["b0"]; pb = p["pull"]["bn"]
    print("=====", pid[:10], "deployer", dep, "b0", b0, "pull", pb, flush=True)
    r = {"back": [], "fwd": []}; cur, before = dep, b0
    for hop in range(3):
        rows = touching([cur], before - 15000, before - 1, desc=True, stop=lambda o: any(x["to"] == cur and x["eth"] > 0 for x in o) and (o[-1]["bn"] < [x for x in o if x["to"] == cur and x["eth"] > 0][0]["bn"] - 200))
        inc = [x for x in rows if x["to"] == cur and x["eth"] > 0]
        print("  back hop", hop + 1, cur); show(inc[:40], lab)
        r["back"].append({"addr": cur, "in": inc})
        if not inc: break
        f = max(inc, key=lambda x: x["eth"])
        if f["nonce"] > 50: print("   stop: funder nonce", f["nonce"]); break
        cur, before = f["from"], f["bn"]
    # forward from pull: deployer's next txs
    rows = touching([dep], pb + 1, pb + 30000, stop=lambda o: any(x["from"] == dep and x["eth"] > 0.01 for x in o))
    print("  fwd deployer"); show(rows, lab); r["fwd"].append(rows)
    big = [x for x in rows if x["from"] == dep and x["eth"] > 0.01]
    if big:
        nx = big[0]["to"]
        rows2 = touching([nx], big[0]["bn"] - 200, big[0]["bn"] + 3000, stop=lambda o: sum(1 for x in o if x["from"] == nx) >= 3)
        print("  around collector", nx); show(rows2, lab); r["fwd"].append(rows2)
    res[pid] = r
    json.dump(res, open(D + "oct9b.json", "w"), indent=1)
