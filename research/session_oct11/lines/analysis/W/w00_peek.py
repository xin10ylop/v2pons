"""peek: the V3 crowd line rows, their launch tx, crowd buy txs (value, input) from analyst C's pickles"""
import pickle, sys, os
from collections import Counter
C = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/analysis/C"
R = pickle.load(open(C + "/v23.pkl", "rb")); E = pickle.load(open(C + "/ev.pkl", "rb")); T = pickle.load(open(C + "/tx.pkl", "rb"))
L = [r for r in R.values() if r["dex"] == "v3" and (r["fam"]["lc"] or "").startswith("0a493d1a") and r["launch"]["selector"] == "ac9650d8"
     and r["launch"]["calldata_len"] == 836 and r["fee"] == 100 and r["launch"]["value_eth"] == 0]
L.sort(key=lambda r: r["launch_block"])
print(len(L))
r = L[-1]
print({k: v for k, v in r.items() if k not in ("fam",)})
print(r["fam"])
t = T.get(r["launch_tx"]); print("launch tx", t)
