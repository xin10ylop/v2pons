"""Population stats of all 7,485 launch txs on launcher 0x3194e326: recipient vs sender, metadata host, 'auto' prefix, event topics."""
import json, collections, sys, re
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch")
from decode import dec
S = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/"
T = json.load(open(S + "launcher_txs.json")); L = json.load(open(S + "launcher_logs.json"))
lg = {x["transactionHash"]: x for x in L}
C = collections.Counter
host = C(); pref = C(); rs = C(); t1 = C(); t2tok = C(); recips = C(); vals = C(); errs = 0; nonhost = []
for h, t in T.items():
    d = dec(t["input"])
    if "err" in d: errs += 1; continue
    u = d["s3"]; m = re.match(r"(https?://[^/]+)", u); hst = m.group(1) if m else u[:40]
    host[hst] += 1
    if "100kdaily" not in u: nonhost.append((t["bn"], t["from"], u[:90]))
    pref["auto" if "launch_auto_" in u else ("launch_" if "/launch_" in u else "other")] += 1
    r = d["recipient"].lower(); recips[r] += 1
    rs[r == t["from"]] += 1
    x = lg.get(h)
    if x: t1[("0x" + x["topics"][1][-40:]) == t["from"]] += 1
print("txs", len(T), "decode errors", errs)
print("metadata hosts:", host.most_common(10))
print("file prefix:", pref)
print("recipient == tx sender:", rs)
print("Launched topic1 == tx sender:", t1)
print("most common recipients:", recips.most_common(5))
print("non-100kdaily metadata examples:", len(nonhost), nonhost[:10])
