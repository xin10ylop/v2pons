"""Token creations on the bonding-curve factory 0xe33e9e47 and the address lists the new curves emit at creation (topic 0xe4b7e48f)."""
import sys, json, time, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops")
from lib import *
F = "0xe33e9e479df8802cb0866d5d05258bec4cf62948"
head = int(rpc("eth_blockNumber", []), 16); START = int(sys.argv[1]) if len(sys.argv) > 1 else 82000000
TC = "0xdcacba5e347ae7ab"; TL = "0xe4b7e48fbd47c2f6"
def getlogs(flt, a, b):
    calls = [("eth_getLogs", [dict(flt, fromBlock=hex(s), toBlock=hex(min(s + 29999, b)))]) for s in range(a, b + 1, 30000)]
    out = []
    for i in range(0, len(calls), 20):
        for k in range(10):
            try:
                r = post([{"jsonrpc": "2.0", "id": j, "method": m, "params": p} for j, (m, p) in enumerate(calls[i:i + 20])])
                if isinstance(r, list) and all("result" in x for x in r): break
            except RuntimeError: pass
            time.sleep(2 + 2 * k)
        else: raise RuntimeError("logs")
        for x in r: out += x["result"]
    return out
cr = getlogs({"address": F}, START, head)
print("factory logs", len(cr), collections.Counter(l["topics"][0][:18] for l in cr))
cre = [l for l in cr if l["topics"][0].startswith(TC)]
json.dump({"start": START, "head": head, "logs": cr}, open(D + "bcurve_factory.json", "w"))
print("creations", len(cre))
