import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
from load_all import load_all
from classify import annotate
pools, head = load_all(); cw = annotate(pools)
lowfee = {p["pid"] for p in pools if p["kind"] == "orig" and p["fee"] < 1000}
out = {"head": head, "deployers": {}, "crowd": sorted(cw)}
for p in pools:
    fam = "copy" if p["kind"] == "copy" else ("orig_lowfee" if p["pid"] in lowfee else "orig")
    out["deployers"][p["deployer"]] = {"pid": p["pid"], "block": p["b0"], "fam": fam, "fee": p["fee"], "pull_block": p["pull"]["bn"] if p["pull"] else None}
json.dump(out, open("deployers.json", "w"))
import collections
print(len(out["deployers"]), "deployers;", collections.Counter(v["fam"] for v in out["deployers"].values()), "; crowd wallets", len(cw), "; head", head)
print("lowfee launches:", sorted((v["block"], v["fee"]) for v in out["deployers"].values() if v["fam"] == "orig_lowfee"))
