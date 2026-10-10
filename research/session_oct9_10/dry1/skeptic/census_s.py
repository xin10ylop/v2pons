"""broader census (own code): v2.433 family launches over the 24 h before the dry-run window plus the window; pull offsets; buys before the bot's first buy"""
import sys, os, pickle, json, collections
SCR = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad"; sys.path.insert(0, SCR)
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, T_ML, W, sgn
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "census_s.pkl")
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; VAL = 2433328500000000000
D = pickle.load(open(os.path.join(HERE, "data_s.pkl"), "rb"))
end = D["start"] - 1; start = end - int(24 * 3600 / 0.1035)
head = int(rpc("eth_blockNumber", []), 16)
C = pickle.load(open(OUT, "rb")) if os.path.exists(OUT) else {}
if "inits" not in C:
    C["inits"] = logs({"address": PM, "topics": [T_INIT]}, start, end); pickle.dump(C, open(OUT, "wb"))
inits = C["inits"]; print("inits", len(inits), "range", start, end)
cand = [l for l in inits if W(l["data"], 0) == 2500 and sgn(W(l["data"], 1)) == 50 and W(l["data"], 2) == 0]
if "ltx" not in C:
    hs = sorted({l["transactionHash"] for l in cand}); C["ltx"] = dict(zip(hs, batch([("eth_getTransactionByHash", [h]) for h in hs]))); pickle.dump(C, open(OUT, "wb"))
fam = []
for l in cand:
    t = C["ltx"][l["transactionHash"]]
    if (t["to"] or "").lower() == POSM and int(t["value"], 16) == VAL and (len(t["input"]) - 2) // 2 == 1444:
        fam.append({"pid": l["topics"][1], "bn": int(l["blockNumber"], 16), "tx": l["transactionHash"], "from": t["from"].lower(), "sp0": W(l["data"], 3), "tick0": sgn(W(l["data"], 4)), "token": l["topics"][3][-40:]})
fam.sort(key=lambda x: x["bn"]); print("family", len(fam))
if "plogs" not in C:
    pl = []
    for i in range(0, len(fam), 20):
        g = fam[i:i+20]
        pl += logs({"address": PM, "topics": [[T_SWAP, T_ML], [x["pid"] for x in g]]}, g[0]["bn"], min(head, g[-1]["bn"] + 6000))
        if i % 100 == 0: print("logs", i, len(pl))
    C["plogs"] = pl; pickle.dump(C, open(OUT, "wb"))
pl = C["plogs"]; print("pool logs", len(pl))
by = collections.defaultdict(list)
for l in pl: by[l["topics"][1]].append(l)
# txs needed: every swap up to and including the first bot buy candidate (first buy >= 0.04 ETH) and every pull tx
need = set()
for x in fam:
    ev = sorted(by[x["pid"]], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    for l in ev:
        if l["topics"][0] == T_ML:
            if sgn(W(l["data"], 2)) < 0: need.add(l["transactionHash"]); break
            continue
        need.add(l["transactionHash"])
        a0 = W(l["data"], 0); a0 = sgn(a0); a0 = a0 - (1 << 128) if a0 >= (1 << 127) else a0
        if -a0 >= int(0.04e18): break
txs = C.get("txs", {})
miss = sorted(h for h in need if h not in txs)
print("txs to fetch", len(miss))
for i in range(0, len(miss), 500):
    r = batch([("eth_getTransactionByHash", [h]) for h in miss[i:i+500]])
    for h, t in zip(miss[i:i+500], r): txs[h] = t
    C["txs"] = txs; pickle.dump(C, open(OUT, "wb")); print("fetched", i + 500)
C["fam"] = fam; C["range"] = (start, end); pickle.dump(C, open(OUT, "wb")); print("done")
