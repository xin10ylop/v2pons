"""one busy census-sample curve: all its own logs in its first 3,000 blocks with the decoded words; and the tx of each distinct topic."""
import json, collections
from krpc import *
B = json.load(open(os.path.join(CEN, "bonding.json")))
s = [x for x in B["sample_txs"] if x["curve"] == "0xe8e324b6f1df780355e091aafe5e4211486965f2"][0]
print(s)
L = logs({"address": s["curve"]}, s["bn"], s["bn"] + 3000)
json.dump({"s": s, "logs": L}, open(os.path.join(DATA, "curve_e8e3_logs.json"), "w"))
seen = collections.Counter()
for l in L:
    t = l["topics"][0][:10]; seen[t] += 1
    if seen[t] <= 4:
        d = l["data"]; ws = [W(d, i) for i in range((len(d) - 2) // 64)]
        print(int(l["blockNumber"], 16) - s["bn"], t, [A(x) for x in l["topics"][1:]], [w if w < 2**160 or w > 2**200 else hex(w) for w in ws], l["transactionHash"][:12])
print(seen)
