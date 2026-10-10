import sys, os, pickle
SCR = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad"; sys.path.insert(0, SCR)
from chain import batch
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_s.pkl")
D = pickle.load(open(P, "rb"))
hs = sorted({l["transactionHash"] for l in D["logs"]})
have = {}
for b in D["blocks"].values():
    for t in b["transactions"]: have[t["hash"]] = t
miss = [h for h in hs if h not in have]
print(len(hs), "missing", len(miss))
r = batch([("eth_getTransactionByHash", [h]) for h in miss])
for h, t in zip(miss, r): have[h] = t
D["txs"] = {h: have[h] for h in hs}
pickle.dump(D, open(P, "wb")); print("ok")
