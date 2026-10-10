import json, sys, glob
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import batch, T_INIT, PM
D = json.load(open("/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/oct8_pools.json"))
cp = [p for p in D["pools"] if p["kind"] == "copy"]
recs = batch([("eth_getTransactionReceipt", [p["tx"]]) for p in cp])
tokens = {}
for p, r in zip(cp, recs):
    for l in r["logs"]:
        if l["address"].lower() == PM and l["topics"][0] == T_INIT and l["topics"][1] == p["pid"]:
            tokens[l["topics"][3][-40:]] = ("copy", p["block"])
for f in glob.glob("raw/*.json"):
    R = json.load(open(f)); tokens[R["token"].lower()] = ("orig", R["p"]["block"])
print(len(tokens), "tokens")
hits = 0; n = 0
for f in sorted(glob.glob("raw/*.json")):
    R = json.load(open(f)); me = R["token"].lower()
    for b in R["blocks"]:
        for t in b["txs"]:
            if t["input"] is None or t["value"] == 0: continue
            n += 1
            others = [(tk, v) for tk, v in tokens.items() if tk != me and tk in t["input"] and 0 <= b["n"] - v[1] <= 3000]
            if others: hits += 1; print("tx carries another armed token:", R["p"]["block"], b["n"] - R["p"]["block"], t["h"], t["value"], others)
print("feed txs scanned", n, "with another armed token", hits)
