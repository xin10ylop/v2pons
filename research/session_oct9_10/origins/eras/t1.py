from L import *
X = {x["h"]: x for x in launches()}
x = next(v for v in X.values() if v["from"] == "0x6ea95d3df055989aa4d9e2567fab035d19cfbc52")
print(x)
ml = logs({"address": PM, "topics": [T_ML, x["pid"]]}, x["bn"], x["bn"] + 5000)
for l in ml: print("ML", int(l["blockNumber"], 16), sgn(W(l["data"], 2)) / 1e18, l["transactionHash"][:12])
pull = min(int(l["blockNumber"], 16) for l in ml if sgn(W(l["data"], 2)) < 0)
tr = logs({"address": x["token"], "topics": [T_TR]}, x["bn"], pull + 200)
crowdA = set(json.load(open(S + "money/pots.json"))["pots"]["A_7.01"]["crowd"])
c = collections.Counter()
for l in tr:
    f, t = a32(l["topics"][1]), a32(l["topics"][2])
    tag = "PM->" if f == PM else ("->PM" if t == PM else "")
    print(int(l["blockNumber"], 16) - x["bn"], f[:10], t[:10], tag, "crowdA" if (t in crowdA or f in crowdA) else "")
