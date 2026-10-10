"""B-launch deployers: funding (scan back from the launch for a plain transfer to it / input naming it) and every tx they sent after the pull."""
import sys, json, os
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops")
from lib import *
L = json.load(open(D + "b_launches.json"))
FN = D + "deployers_fund.json"
res = json.load(open(FN)) if os.path.exists(FN) else {}
for pid, p in sorted(L.items(), key=lambda kv: kv[1]["b0"]):
    dep = p["deployer"]; b0 = p["b0"]; n = nonce_now(dep)
    print("==", utc(p["ts"]), pid[:10], "deployer", dep, "nonce now", n, flush=True)
    r = res.get(pid) or {"deployer": dep}
    r["nonce_now"] = n
    if "funding" not in r:
        r["funding"] = scan(b0 - 40000, b0 - 1, lambda x, t: (x["to"] == dep and x["value"] > 0) or (dep[2:] in t["input"].lower() and x["from"] != dep), backwards=True,
                 stop=lambda h: any(y["to"] == dep and y["value"] > 0 for y in h))
    for y in r["funding"]: print("   in :", y["bn"], b0 - y["bn"], "blocks before launch", utc(y["ts"]), y["from"], "->", y["to"], round(y["value"], 6), y["sel"], "nonce", y["nonce"], y["hash"], flush=True)
    if p["pull"] and "after" not in r:
        pb = p["pull"]["bn"]; pn = int(rpc("eth_getTransactionByHash", [p["pull"]["tx"]])["nonce"], 16)
        r["pull_nonce"] = pn
        r["after"] = scan(pb + 1, pb + 60000, lambda x, t: x["from"] == dep or (x["to"] == dep and x["value"] > 0), stop=lambda h: sum(1 for y in h if y["from"] == dep) >= n - 1 - pn)
    for y in r.get("after", []): print("   out:", y["bn"], "+%d after pull" % (y["bn"] - p["pull"]["bn"]), utc(y["ts"]), y["from"], "->", y["to"], round(y["value"], 6), y["sel"], "nonce", y["nonce"], y["hash"], flush=True)
    res[pid] = r
    json.dump(res, open(FN, "w"), indent=1)
