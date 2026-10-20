import pickle, collections, statistics as st, math
P = pickle.load(open("pools.pkl", "rb"))
Z = "0x" + "0" * 40
c = collections.Counter()
rows = []
for p in P.values():
    if "sw" not in p: c["nologs"] += 1; continue
    if p["hooks"] != Z: c["hooks"] += 1; continue
    real = [x for x in p["sw"] if -x[2] >= 2e14]
    c["nohook"] += 1
    if not real: c["noreal"] += 1; continue
    c["withreal"] += 1
    rows.append(p)
print(c)
by = collections.Counter()
for p in rows:
    key = (p["to"], p["sel"], p["fee"])
    by[key] += 1
for k, v in by.most_common(40): print(v, k)
print("fee dist among withreal", collections.Counter(p["fee"] for p in rows).most_common(20))
