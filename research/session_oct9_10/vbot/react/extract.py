#!/usr/bin/env python3
"""Extract the PM1444 families' (v3.0, v5.0, v2.433) census rows and pool logs into vbot/fam.pkl."""
import json, pickle, os
O = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/others"
R = [json.loads(l) for l in open(os.path.join(O, "census.jsonl"))]
def fam(r):
    if r["sel"] != "0xac9650d8" or r["inlen"] != 1444 or r["hooks"] != "0x" + "0" * 40: return None
    if r["fee"] == 10000 and r["ts"] == 200 and round(r["value"] or 0, 3) == 3.0: return "v3.0"
    if r["fee"] == 10000 and r["ts"] == 200 and round(r["value"] or 0, 3) == 5.0: return "v5.0"
    if r["fee"] == 2500 and r["ts"] == 50: return "v2.433"
    return None
rows = {r["pid"]: dict(r, fam=fam(r)) for r in R if fam(r)}
pl = pickle.load(open(os.path.join(O, "cache_plogs.pkl"), "rb"))
inits = {l["topics"][1]: l for l in pickle.load(open(os.path.join(O, "cache_inits.pkl"), "rb"))["logs"]}
txs = pickle.load(open(os.path.join(O, "cache_txs.pkl"), "rb"))
out = {"rows": rows, "plogs": {p: pl.get(p, []) for p in rows}, "inits": {p: inits[p] for p in rows}, "launchtx": {r["tx"]: txs.get(r["tx"]) for r in rows.values()}}
pickle.dump(out, open("fam.pkl", "wb"))
import collections
print(collections.Counter(r["fam"] for r in rows.values()), sum(len(v) for v in out["plogs"].values()))
